"""
Conexão e operações com PostgreSQL (TimescaleDB).
Gerencia a criação das tabelas e inserção de registros de tráfego.
"""

import os
import logging
from datetime import datetime

import psycopg2
from psycopg2.extras import execute_values, RealDictCursor

DATABASE_URL = os.environ["DATABASE_URL"]

logger = logging.getLogger(__name__)

CREATE_TRAFFIC_TABLE = """
CREATE TABLE IF NOT EXISTS traffic_records (
    id                  SERIAL PRIMARY KEY,
    collected_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    route_id            TEXT NOT NULL,
    duration_seconds    INT,
    duration_in_traffic INT,
    distance_meters     INT,
    rain_mm             FLOAT DEFAULT 0,
    temp_celsius        FLOAT,
    humidity            INT,
    weather_main        TEXT,
    hour_of_day         INT,
    day_of_week         INT,
    is_weekend          BOOLEAN,
    is_rush_hour        BOOLEAN
);
"""

CREATE_HYPERTABLE = """
SELECT create_hypertable(
    'traffic_records', 'collected_at',
    if_not_exists => TRUE
);
"""

CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_traffic_route_time
    ON traffic_records (route_id, collected_at DESC);
"""


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    """Cria tabelas e hypertable do TimescaleDB se não existirem."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        
        # 1. Cria a tabela base
        cur.execute(CREATE_TRAFFIC_TABLE)
        conn.commit()
        
        # 2. Tenta converter em hypertable (específico do TimescaleDB)
        try:
            cur.execute(CREATE_HYPERTABLE)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.warning(f"Aviso ao criar hypertable (pode já existir): {e}")
            
        # 3. Cria índices
        cur.execute(CREATE_INDEX)
        conn.commit()
    finally:
        conn.close()
    logger.info("Banco de dados inicializado.")


def save_record(rec: dict):
    """
    Insere um registro de tráfego enriquecido com features temporais.
    """
    now = datetime.now()
    rec["hour_of_day"] = now.hour
    rec["day_of_week"] = now.weekday()  # 0=segunda, 6=domingo
    rec["is_weekend"] = now.weekday() >= 5
    rec["is_rush_hour"] = (
        now.hour in range(6, 9) or now.hour in range(17, 20)
    )

    cols = list(rec.keys())
    vals = [list(rec.values())]

    with get_conn() as conn:
        cur = conn.cursor()
        execute_values(
            cur,
            f"INSERT INTO traffic_records ({', '.join(cols)}) VALUES %s",
            vals,
        )
        conn.commit()
    logger.info(f"Registro salvo: {rec.get('route_id')} | trânsito={rec.get('duration_in_traffic')}s | chuva={rec.get('rain_mm')}mm")


def fetch_recent(route_id: str, limit: int = 10) -> list[dict]:
    """Retorna os últimos N registros de uma rota para o dashboard."""
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT * FROM traffic_records
            WHERE route_id = %s
            ORDER BY collected_at DESC
            LIMIT %s
            """,
            (route_id, limit),
        )
        return [dict(row) for row in cur.fetchall()]
