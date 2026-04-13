from pydantic import BaseModel, Field
from datetime import datetime


class PredictRequest(BaseModel):
    route_id: str = Field(..., example="mangabeira_centro")
    rain_mm: float = Field(0.0, ge=0, example=5.2)
    temp_celsius: float = Field(28.0, example=29.5)
    humidity: int = Field(75, ge=0, le=100, example=82)
    lag_15min: float = Field(..., description="Duração em trânsito da leitura anterior (segundos)")
    lag_30min: float = Field(..., description="Leitura de 30min atrás")
    lag_60min: float = Field(..., description="Leitura de 60min atrás")
    lag_90min: float = Field(..., description="Leitura de 90min atrás")
    rolling_mean_1h: float = Field(..., description="Média da última hora")
    rolling_std_1h: float = Field(0.0, description="Desvio padrão da última hora")
    rolling_max_1h: float = Field(0.0, description="Máximo da última hora")
    same_hour_last_week: float = Field(0.0, description="Média histórica desta hora")
    current_delay_ratio: float = Field(1.0, description="Razão atual: tempo_tráfego / tempo_normal")


class ForecastItem(BaseModel):
    probability: float
    severity: str
    alert: bool

class PredictResponse(BaseModel):
    route_id: str
    delay_probability: float
    alert: bool
    severity: str
    forecasts: dict[str, ForecastItem] | None = None
    trend: str | None = "stable"
    timestamp: datetime


class RouteStats(BaseModel):
    route_id: str
    label: str
    avg_duration_traffic: float | None
    avg_duration_seconds: float | None
    max_delay_ratio: float | None
    total_records: int


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    db_connected: bool
