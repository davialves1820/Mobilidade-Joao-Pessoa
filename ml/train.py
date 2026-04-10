"""
Treinamento do modelo XGBoost para predição de atrasos de tráfego em JP.

Uso:
    cd ml
    python train.py

Requisitos: ao menos ~500 registros no banco (≈ 5 dias de coleta contínua).
"""

import os
import sys
import logging

import pandas as pd
import numpy as np
import joblib
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import (
    classification_report,
    roc_auc_score,
    confusion_matrix,
)
import psycopg2
from dotenv import load_dotenv

# Permite rodar o script de qualquer pasta
sys.path.insert(0, os.path.dirname(__file__))
from features import build_features, get_feature_matrix, FEATURE_COLS

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train")

DATABASE_URL = os.environ["DATABASE_URL"]
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")


def load_data() -> pd.DataFrame:
    """Carrega todos os registros do banco."""
    with psycopg2.connect(DATABASE_URL) as conn:
        df = pd.read_sql(
            "SELECT * FROM traffic_records ORDER BY collected_at",
            conn,
            parse_dates=["collected_at"],
        )
    logger.info(f"Carregados {len(df):,} registros do banco.")
    return df


def train():
    df_raw = load_data()

    if len(df_raw) < 100:
        logger.error("Dados insuficientes. Colete ao menos 100 registros antes de treinar.")
        sys.exit(1)

    X, y = get_feature_matrix(df_raw)
    logger.info(f"Dataset: {len(X):,} amostras | {y.mean():.1%} positivos (atraso)")

    # TimeSeriesSplit respeita a ordem temporal — não vaza dados futuros
    tscv = TimeSeriesSplit(n_splits=5)

    model = xgb.XGBClassifier(
        n_estimators=400,
        max_depth=5,
        learning_rate=0.04,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=max(1, int((y == 0).sum() / max((y == 1).sum(), 1))),
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )

    auc_scores = []
    for fold, (train_idx, val_idx) in enumerate(tscv.split(X), 1):
        X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]

        model.fit(
            X_tr, y_tr,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )

        preds = model.predict(X_val)
        proba = model.predict_proba(X_val)[:, 1]
        auc = roc_auc_score(y_val, proba)
        auc_scores.append(auc)

        logger.info(f"\n{'='*40}\nFold {fold} — AUC: {auc:.3f}")
        logger.info(f"\n{classification_report(y_val, preds, target_names=['Normal', 'Atraso'])}")

    logger.info(f"\nAUC médio (5-fold): {np.mean(auc_scores):.3f} ± {np.std(auc_scores):.3f}")

    # Treina no dataset completo para salvar
    model.fit(X, y, verbose=False)

    # Importância das features
    importances = pd.Series(model.feature_importances_, index=FEATURE_COLS)
    logger.info(f"\nTop 10 features:\n{importances.nlargest(10).to_string()}")

    joblib.dump(model, MODEL_PATH)
    logger.info(f"\nModelo salvo em: {MODEL_PATH}")


if __name__ == "__main__":
    train()
