"""
Módulo de avaliação de performance para o portfólio.
Gera métricas detalhadas, curvas ROC e análise de importância de features.

Uso:
    python ml/evaluate.py
"""

import os
import logging
import pandas as pd
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import roc_curve, auc, confusion_matrix, classification_report
from train import load_data
from features import get_feature_matrix, FEATURE_COLS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate")

PLOTS_DIR = os.path.join(os.path.dirname(__file__), "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)


def evaluate():
    logger.info("Iniciando avaliação técnica dos modelos...")
    df_raw = load_data()
    
    # Usamos os últimos 20% dos dados como teste final (hold-out temporal)
    split_idx = int(len(df_raw) * 0.8)
    df_test_raw = df_raw.iloc[split_idx:]
    
    horizons = ["15m", "30m", "60m"]
    results = {}

    plt.figure(figsize=(10, 8))
    
    for hz in horizons:
        model_path = os.path.join(os.path.dirname(__file__), f"model_{hz}.pkl")
        if not os.path.exists(model_path):
            logger.warning(f"Modelo para {hz} não encontrado. Pulei.")
            continue
            
        model = joblib.load(model_path)
        X_test, y_test = get_feature_matrix(df_test_raw, target_col=f"target_{hz}")
        
        if len(X_test) == 0:
            logger.warning(f"Sem amostras de teste suficientes para {hz}.")
            continue

        y_prob = model.predict_proba(X_test)[:, 1]
        y_pred = model.predict(X_test)
        
        # 1. Curva ROC
        fpr, tpr, _ = roc_curve(y_test, y_prob)
        roc_auc = auc(fpr, tpr)
        plt.plot(fpr, tpr, label=f"Horizonte {hz} (AUC = {roc_auc:.2f})")
        
        results[hz] = {
            "auc": roc_auc,
            "report": classification_report(y_test, y_pred),
            "cm": confusion_matrix(y_test, y_pred)
        }
        
        # 2. Importância de Features (apenas para o modelo principal de 15m)
        if hz == "15m":
            save_feature_importance(model)
            save_confusion_matrix(y_test, y_pred, hz)

    # Finaliza e salva Curva ROC
    plt.plot([0, 1], [0, 1], "k--")
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel("Taxa de Falsos Positivos")
    plt.ylabel("Taxa de Verdadeiros Positivos")
    plt.title("Curvas ROC por Horizonte de Predição")
    plt.legend(loc="lower right")
    plt.savefig(os.path.join(PLOTS_DIR, "roc_curves.png"))
    plt.close()
    
    save_text_report(results)
    logger.info(f"Avaliação concluída! Gráficos e relatório salvos em: {PLOTS_DIR}")


def save_feature_importance(model):
    importances = model.feature_importances_
    feat_imp = pd.Series(importances, index=FEATURE_COLS).sort_values(ascending=True)
    
    plt.figure(figsize=(10, 7))
    feat_imp.plot(kind="barh", color="skyblue")
    plt.title("Importância das Features (Horizonte 15m)")
    plt.xlabel("Peso no XGBoost")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "feature_importance.png"))
    plt.close()


def save_confusion_matrix(y_true, y_pred, hz):
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", 
                xticklabels=["Normal", "Atraso"], 
                yticklabels=["Normal", "Atraso"])
    plt.title(f"Matriz de Confusão - {hz}")
    plt.ylabel("Real")
    plt.xlabel("Predição")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, f"confusion_matrix_{hz}.png"))
    plt.close()


def save_text_report(results):
    report_path = os.path.join(PLOTS_DIR, "evaluation_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Relatório Técnico de Performance do Modelo\n\n")
        f.write("Este documento contém a análise de performance hold-out (últimos 20% dos dados historicos).\n\n")
        
        for hz, res in results.items():
            f.write(f"## Horizonte: {hz}\n")
            f.write(f"- **AUC-ROC**: {res['auc']:.4f}\n\n")
            f.write("### Relatório de Classificação:\n")
            f.write(f"```text\n{res['report']}\n```\n\n")
            f.write("---\n\n")


if __name__ == "__main__":
    evaluate()
