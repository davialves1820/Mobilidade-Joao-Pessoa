"""
FastAPI — API de predição de atrasos de tráfego em João Pessoa.
Expõe endpoints REST para o dashboard Streamlit e integrações externas.
"""

import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from schemas import PredictRequest, PredictResponse, RouteStats, HealthResponse
from predict import predict_delay, _load_model

logger = logging.getLogger("api")
DATABASE_URL = os.environ["DATABASE_URL"]

ROUTE_LABELS = {
    "mangabeira_centro": "Mangabeira-Centro",
    "epitacio_beira_rio": "Epitácio-Beira Rio",
    "br230_mangabeira": "BR-230-Mangabeira",
    "altiplano_centro": "Altiplano-Centro",
    "bessa_centro": "Bessa-Centro",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Carregando modelo...")
    _load_model()
    logger.info("Modelo carregado.")
    yield


app = FastAPI(
    title="Mobilidade JP — API de Predições",
    description="Previsão de atrasos de tráfego em João Pessoa com ML",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_conn():
    return psycopg2.connect(DATABASE_URL)


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["infra"])
def health():
    model_ok = True
    db_ok = True
    try:
        _load_model()
    except Exception:
        model_ok = False
    try:
        with get_conn() as conn:
            conn.cursor().execute("SELECT 1")
    except Exception:
        db_ok = False

    return HealthResponse(
        status="ok" if (model_ok and db_ok) else "degraded",
        model_loaded=model_ok,
        db_connected=db_ok,
    )


@app.post("/predict", response_model=PredictResponse, tags=["ml"])
def predict(req: PredictRequest):
    """
    Retorna probabilidade de atraso para a próxima janela de 15 minutos
    numa rota específica de João Pessoa.
    """
    try:
        result = predict_delay(
            rain_mm=req.rain_mm,
            temp_celsius=req.temp_celsius,
            humidity=req.humidity,
            lag_15min=req.lag_15min,
            lag_30min=req.lag_30min,
            lag_60min=req.lag_60min,
            lag_90min=req.lag_90min,
            rolling_mean_1h=req.rolling_mean_1h,
            rolling_std_1h=req.rolling_std_1h,
            rolling_max_1h=req.rolling_max_1h,
            same_hour_last_week=req.same_hour_last_week,
            current_delay_ratio=req.current_delay_ratio,
        )
        return PredictResponse(route_id=req.route_id, **result)
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Modelo não encontrado. Execute ml/train.py primeiro.",
        )
    except Exception as e:
        logger.error(f"Erro na predição: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/routes/{route_id}/predict", response_model=PredictResponse, tags=["ml"])
def predict_current(route_id: str):
    """
    Realiza predição para o momento atual buscando os últimos dados do banco.
    Facilita a integração com o dashboard.
    """
    if route_id not in ROUTE_LABELS:
        raise HTTPException(status_code=404, detail="Rota não encontrada.")

    try:
        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)

            # 1. Pega a leitura mais recente (para clima e dados base)
            cur.execute(
                "SELECT * FROM traffic_records WHERE route_id = %s ORDER BY collected_at DESC LIMIT 1",
                (route_id,)
            )
            latest = cur.fetchone()
            if not latest:
                raise HTTPException(status_code=404, detail="Sem dados históricos para esta rota.")

            # 2. Pega lags (15, 30, 60, 90 min) - simplificado pegando as últimas 10 leituras
            cur.execute(
                "SELECT duration_in_traffic FROM traffic_records WHERE route_id = %s ORDER BY collected_at DESC LIMIT 10",
                (route_id,)
            )
            history = [r["duration_in_traffic"] for r in cur.fetchall()]
            
            # 3. Estatísticas de 1h (últimas 4 leituras se coletadas a cada 15m)
            stats_1h = history[:4]
            
            # Preenche valores caso o histórico seja curto
            def get_lag(idx, default): return history[idx] if len(history) > idx else default

            # 4. Pega dados de exatamente 7 dias atrás
            cur.execute(
                "SELECT duration_in_traffic FROM traffic_records WHERE route_id = %s AND collected_at <= %s ORDER BY collected_at DESC LIMIT 1",
                (route_id, latest["collected_at"] - timedelta(days=7))
            )
            last_week_record = cur.fetchone()
            last_week_val = last_week_record["duration_in_traffic"] if last_week_record else latest["duration_in_traffic"]

            res = predict_delay(
                rain_mm=float(latest["rain_mm"]),
                temp_celsius=float(latest["temp_celsius"]),
                humidity=int(latest["humidity"]),
                lag_15min=float(get_lag(1, latest["duration_in_traffic"])),
                lag_30min=float(get_lag(2, latest["duration_in_traffic"])),
                lag_60min=float(get_lag(4, latest["duration_in_traffic"])),
                lag_90min=float(get_lag(6, latest["duration_in_traffic"])),
                rolling_mean_1h=float(sum(stats_1h)/len(stats_1h)),
                rolling_std_1h=0.0, # simplificado para o dashboard
                rolling_max_1h=float(max(stats_1h)),
                same_hour_last_week=float(last_week_val),
                current_delay_ratio=float(latest["duration_in_traffic"] / latest["duration_seconds"]),
            )
            return PredictResponse(route_id=route_id, **res)

    except Exception as e:
        logger.error(f"Erro na predição facilitada: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/routes/stats", response_model=list[RouteStats], tags=["dados"])
def route_stats():
    """Retorna estatísticas agregadas de cada rota nas últimas 24h."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT
                route_id,
                AVG(duration_in_traffic) AS avg_duration_traffic,
                AVG(duration_seconds) AS avg_duration_seconds,
                MAX(duration_in_traffic::float / NULLIF(duration_seconds, 0)) AS max_delay_ratio,
                COUNT(*) AS total_records
            FROM traffic_records
            WHERE collected_at >= %s
            GROUP BY route_id
            ORDER BY route_id
            """,
            (cutoff,),
        )
        rows = cur.fetchall()

    return [
        RouteStats(
            route_id=r["route_id"],
            label=ROUTE_LABELS.get(r["route_id"], r["route_id"]),
            avg_duration_traffic=r["avg_duration_traffic"],
            avg_duration_seconds=r["avg_duration_seconds"],
            max_delay_ratio=r["max_delay_ratio"],
            total_records=r["total_records"],
        )
        for r in rows
    ]


@app.get("/history", tags=["dados"])
def global_history(hours: int = 6):
    """Retorna histórico de todas as rotas para o gráfico comparativo."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT
                collected_at,
                route_id,
                duration_in_traffic,
                duration_seconds,
                temp_celsius,
                rain_mm
            FROM traffic_records
            WHERE collected_at >= %s
            ORDER BY collected_at ASC
            """,
            (cutoff,),
        )
        rows = cur.fetchall()
    return rows


@app.get("/routes/{route_id}/history", tags=["dados"])
def route_history(route_id: str, hours: int = 6):
    """Retorna histórico recente de uma específica."""
    if route_id not in ROUTE_LABELS:
        raise HTTPException(status_code=404, detail="Rota não encontrada.")
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT
                collected_at,
                duration_in_traffic,
                duration_seconds,
                rain_mm,
                ROUND((duration_in_traffic::numeric / NULLIF(duration_seconds, 0) - 1) * 100, 1)
                    AS delay_pct
            FROM traffic_records
            WHERE route_id = %s AND collected_at >= %s
            ORDER BY collected_at ASC
            """,
            (route_id, cutoff),
        )
        rows = cur.fetchall()
    return {"route_id": route_id, "records": rows}
