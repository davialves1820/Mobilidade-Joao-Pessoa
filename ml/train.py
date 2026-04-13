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

    horizons = ["15m", "30m", "60m"]
    
    for hz in horizons:
        target_col = f"target_{hz}"
        logger.info(f"\n{'>'*10} Treinando modelo para +{hz} {'>'*10}")
        
        try:
            X, y = get_feature_matrix(df_raw, target_col=target_col)
        except Exception as e:
            logger.warning(f"Pulo treinamento para {hz}: {e}")
            continue

        if len(X) < 50:
            logger.warning(f"Amostras insuficientes para horizonte {hz} ({len(X)}).")
            continue

        logger.info(f"Dataset: {len(X):,} amostras | {y.mean():.1%} positivos (atraso)")

        model = xgb.XGBClassifier(
            n_estimators=400,
            max_depth=5,
            learning_rate=0.04,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=max(1, int((y == 0).sum() / max((y == 1).sum(), 1))),
            eval_metric="logloss",
            random_state=42,
            n_jobs=-1,
        )

        # Treina no dataset completo (simplificado para multi-modelos)
        model.fit(X, y, verbose=False)

        path = os.path.join(os.path.dirname(__file__), f"model_{hz}.pkl")
        joblib.dump(model, path)
        logger.info(f"Modelo salvo em: {path}")
        
        # Compatibilidade com a API antiga: salva o de 15m como model.pkl também
        if hz == "15m":
            old_path = os.path.join(os.path.dirname(__file__), "model.pkl")
            joblib.dump(model, old_path)

    logger.info("\nTreinamento de múltiplos horizontes concluído!")


if __name__ == "__main__":
    train()
