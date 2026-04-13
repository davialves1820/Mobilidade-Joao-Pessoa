"""
Módulo de inferência — carrega o modelo treinado e faz predições.
Usado tanto pela FastAPI quanto para testes rápidos no terminal.
"""

import os
from datetime import datetime

import joblib
import numpy as np

MODELS_DIR = os.path.dirname(__file__)
_models = {}

def _load_model():
    global _models
    if not _models:
        for hz in ["15m", "30m", "60m"]:
            path = os.path.join(MODELS_DIR, f"model_{hz}.pkl")
            if os.path.exists(path):
                _models[hz] = joblib.load(path)
            elif hz == "15m" and os.path.exists(os.path.join(MODELS_DIR, "model.pkl")):
                # Fallback para o modelo antigo
                _models[hz] = joblib.load(os.path.join(MODELS_DIR, "model.pkl"))
    return _models


def predict_delay(
    rain_mm: float,
    temp_celsius: float,
    humidity: int,
    lag_15min: float,
    lag_30min: float,
    lag_60min: float,
    lag_90min: float,
    rolling_mean_1h: float,
    rolling_std_1h: float = 0.0,
    rolling_max_1h: float = 0.0,
    same_hour_last_week: float = 0.0,
    current_delay_ratio: float = 1.0,
    dt: datetime | None = None,
) -> dict:
    """
    Retorna projeções de atraso para múltiplos horizontes (15, 30, 60 min).
    """
    if dt is None:
        dt = datetime.now()

    models = _load_model()
    if not models:
        raise FileNotFoundError("Nenhum modelo (.pkl) encontrado na pasta da API.")

    features = np.array([[
        dt.hour,
        dt.weekday(),
        int(dt.weekday() >= 5),
        int(dt.hour in range(6, 9) or dt.hour in range(17, 20)),
        rain_mm,
        temp_celsius,
        humidity,
        int(rain_mm > 0.5),
        lag_15min,
        lag_30min,
        lag_60min,
        lag_90min,
        rolling_mean_1h,
        rolling_std_1h,
        rolling_max_1h,
        same_hour_last_week,
        current_delay_ratio,
    ]])

    forecasts = {}
    
    for hz, model in models.items():
        prob = float(model.predict_proba(features)[0][1])
        
        if prob >= 0.70:
            severity = "alto"
        elif prob >= 0.40:
            severity = "médio"
        else:
            severity = "baixo"
            
        forecasts[hz] = {
            "probability": round(prob, 3),
            "severity": severity,
            "alert": prob >= 0.55
        }

    # Calcula tendência (baseada na diferença entre 60m e 15m)
    p15 = forecasts.get("15m", {}).get("probability", 0)
    p60 = forecasts.get("60m", {}).get("probability", 0)
    
    if p60 > p15 + 0.15:
        trend = "increasing"
    elif p60 < p15 - 0.15:
        trend = "decreasing"
    else:
        trend = "stable"

    return {
        "delay_probability": p15, # Para retrocompatibilidade
        "alert": forecasts.get("15m", {}).get("alert", False), # Para retrocompatibilidade
        "severity": forecasts.get("15m", {}).get("severity", "baixo"), # Para retrocompatibilidade
        "forecasts": forecasts,
        "trend": trend,
        "timestamp": dt.isoformat(),
    }
