"""
Módulo de inferência — carrega o modelo treinado e faz predições.
Usado tanto pela FastAPI quanto para testes rápidos no terminal.
"""

import os
from datetime import datetime

import joblib
import numpy as np

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")

_model = None


def _load_model():
    global _model
    if _model is None:
        _model = joblib.load(MODEL_PATH)
    return _model


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
    Retorna a probabilidade de atraso para a próxima janela de 15 minutos.

    Returns:
        dict com delay_probability (0–1), alert (bool), severity (str)
    """
    if dt is None:
        dt = datetime.now()

    model = _load_model()

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

    prob = float(model.predict_proba(features)[0][1])

    if prob >= 0.75:
        severity = "alto"
    elif prob >= 0.50:
        severity = "médio"
    else:
        severity = "baixo"

    return {
        "delay_probability": round(prob, 3),
        "alert": prob >= 0.55,
        "severity": severity,
        "timestamp": dt.isoformat(),
    }
