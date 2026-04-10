"""
Gerador de dados sintéticos para treino do modelo sem coleta real.
Simula 4 semanas de leituras a cada 15 minutos com padrões reais de JP:

  - Pico da manhã (6h–9h) e tarde (17h–20h) em dias úteis
  - Impacto de chuva no trânsito (frequente no litoral de JP)
  - Variação por rota (Mangabeira–Centro é mais lenta que Altiplano)
  - Ruído gaussiano para realismo
  - Eventos de congestionamento esporádicos

Uso:
    python generate_synthetic_data.py
    # ou com mais semanas:
    python generate_synthetic_data.py --weeks 8
"""

import argparse
import logging
import os
import random
from datetime import datetime, timedelta

import numpy as np
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("synth")

DATABASE_URL = os.environ["DATABASE_URL"]

# ──────────────────────────────────────────────
# Perfis por rota — tempos base em segundos
# ──────────────────────────────────────────────
ROUTE_PROFILES = {
    "mangabeira_centro": {
        "base_duration": 1200,   # 20 min sem trânsito
        "distance": 8500,
        "peak_factor": 1.85,     # chega a quase 37 min no pico
        "rain_sensitivity": 1.4, # muito afetada pela chuva
    },
    "epitacio_beira_rio": {
        "base_duration": 900,
        "distance": 6200,
        "peak_factor": 1.60,
        "rain_sensitivity": 1.3,
    },
    "br230_mangabeira": {
        "base_duration": 720,
        "distance": 4800,
        "peak_factor": 1.50,
        "rain_sensitivity": 1.25,
    },
    "altiplano_centro": {
        "base_duration": 1080,
        "distance": 7300,
        "peak_factor": 1.45,
        "rain_sensitivity": 1.2,
    },
    "bessa_centro": {
        "base_duration": 1320,   # 22 min sem trânsito
        "distance": 9800,
        "peak_factor": 1.70,
        "rain_sensitivity": 1.35,
    },
}

# Distribuição de chuva em JP: ~120 dias/ano com chuva, concentrada mar–jul
# Probabilidade de chuva por mês (0–1)
RAIN_PROB_BY_MONTH = {
    1: 0.15, 2: 0.20, 3: 0.30, 4: 0.35,
    5: 0.40, 6: 0.45, 7: 0.40, 8: 0.20,
    9: 0.15, 10: 0.10, 11: 0.10, 12: 0.12,
}


def _congestion_factor(hour: int, weekday: int) -> float:
    """Fator de congestionamento por horário e dia da semana."""
    if weekday >= 5:
        # Fim de semana: trânsito bem mais leve
        if 10 <= hour <= 14:
            return 1.15   # movimento de lazer/praia
        return 1.0

    # Dias úteis
    if 6 <= hour < 8:
        return 1.55   # pico manhã crescendo
    if 8 <= hour < 9:
        return 1.85   # pico máximo manhã
    if 9 <= hour < 10:
        return 1.45   # dissipando
    if 10 <= hour < 17:
        return 1.10   # fluxo normal
    if 17 <= hour < 18:
        return 1.60   # pico tarde crescendo
    if 18 <= hour < 19:
        return 1.90   # pico máximo tarde
    if 19 <= hour < 20:
        return 1.55   # dissipando
    if 20 <= hour < 22:
        return 1.15
    return 1.0        # madrugada


def _generate_weather_for_day(dt: datetime) -> list[dict]:
    """
    Gera condições climáticas para cada 15min de um dia.
    Se chove, dura algumas horas seguidas (realismo).
    """
    month = dt.month
    rain_prob = RAIN_PROB_BY_MONTH.get(month, 0.15)
    slots_per_day = 96  # 24h / 15min

    weather_slots = []
    raining = False
    rain_end_slot = 0
    rain_intensity = 0.0

    for slot in range(slots_per_day):
        hour = (slot * 15) // 60

        # Começo de evento de chuva
        if not raining and random.random() < rain_prob / slots_per_day * 3:
            raining = True
            duration_slots = random.randint(4, 20)  # 1h a 5h de chuva
            rain_end_slot = slot + duration_slots
            rain_intensity = random.uniform(0.5, 25.0)  # mm

        if raining and slot >= rain_end_slot:
            raining = False
            rain_intensity = 0.0

        temp = 28.0 + 4 * np.sin((hour - 6) * np.pi / 12) + random.gauss(0, 0.8)
        humidity = 75 + (15 if raining else 0) + random.gauss(0, 3)

        weather_slots.append({
            "rain_1h": rain_intensity if raining else 0.0,
            "temp": round(np.clip(temp, 22, 36), 1),
            "humidity": int(np.clip(humidity, 55, 99)),
            "weather_main": "Rain" if raining else "Clear",
        })

    return weather_slots


def generate_records(weeks: int = 4) -> list[dict]:
    """Gera todos os registros sintéticos."""
    now = datetime.now().replace(second=0, microsecond=0)
    # começa `weeks` atrás
    start = now - timedelta(weeks=weeks)
    # arredonda para o próximo slot de 15min
    start = start.replace(minute=(start.minute // 15) * 15)

    records = []
    current_day = None
    weather_slots = []

    ts = start
    while ts <= now:
        # Gera clima do dia uma vez por dia
        day = ts.date()
        if day != current_day:
            current_day = day
            weather_slots = _generate_weather_for_day(ts)

        slot_idx = (ts.hour * 60 + ts.minute) // 15
        weather = weather_slots[slot_idx] if slot_idx < len(weather_slots) else weather_slots[-1]

        for route_id, profile in ROUTE_PROFILES.items():
            base = profile["base_duration"]
            cf = _congestion_factor(ts.hour, ts.weekday())
            rain_factor = 1.0

            if weather["rain_1h"] > 10:
                rain_factor = profile["rain_sensitivity"]
            elif weather["rain_1h"] > 3:
                rain_factor = 1.0 + (profile["rain_sensitivity"] - 1) * 0.6
            elif weather["rain_1h"] > 0.5:
                rain_factor = 1.0 + (profile["rain_sensitivity"] - 1) * 0.25

            # Evento esporádico de congestionamento (acidente, obra, etc.)
            extra = 1.0
            if random.random() < 0.02:   # 2% de chance por leitura
                extra = random.uniform(1.3, 2.0)

            duration_in_traffic = int(base * cf * rain_factor * extra * random.gauss(1.0, 0.05))
            duration_in_traffic = max(base, duration_in_traffic)  # nunca menor que o base

            records.append({
                "collected_at": ts,
                "route_id": route_id,
                "duration_seconds": base,
                "duration_in_traffic": duration_in_traffic,
                "distance_meters": profile["distance"],
                "rain_mm": round(weather["rain_1h"], 2),
                "temp_celsius": weather["temp"],
                "humidity": weather["humidity"],
                "weather_main": weather["weather_main"],
                "hour_of_day": ts.hour,
                "day_of_week": ts.weekday(),
                "is_weekend": ts.weekday() >= 5,
                "is_rush_hour": (6 <= ts.hour < 9) or (17 <= ts.hour < 20),
            })

        ts += timedelta(minutes=15)

    return records


def insert_records(records: list[dict]):
    """Insere todos os registros no banco em batch."""
    if not records:
        logger.info("Nenhum registro para inserir.")
        return

    cols = list(records[0].keys())
    values = []
    for r in records:
        row = []
        for c in cols:
            val = r[c]
            # Convert numpy types to native Python types
            if hasattr(val, 'item'):
                val = val.item()
            row.append(val)
        values.append(row)

    with psycopg2.connect(DATABASE_URL) as conn:
        cur = conn.cursor()
        execute_values(
            cur,
            f"INSERT INTO traffic_records ({', '.join(cols)}) VALUES %s ON CONFLICT DO NOTHING",
            values,
            page_size=500,
        )
        conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Gera dados sintéticos de tráfego para JP")
    parser.add_argument("--weeks", type=int, default=4, help="Semanas de dados a gerar (padrão: 4)")
    args = parser.parse_args()

    logger.info(f"Gerando {args.weeks} semanas de dados sintéticos...")
    records = generate_records(weeks=args.weeks)

    total = len(records)
    routes = len(ROUTE_PROFILES)
    slots = total // routes
    logger.info(f"Gerados {total:,} registros ({slots:,} leituras × {routes} rotas)")
    logger.info(f"Período: {records[0]['collected_at']} → {records[-1]['collected_at']}")

    # Estatísticas rápidas
    delays = [r["duration_in_traffic"] / r["duration_seconds"] for r in records]
    pct_delayed = sum(1 for d in delays if d > 1.2) / len(delays)
    logger.info(f"Proporção com atraso >20%: {pct_delayed:.1%} (target do modelo)")

    logger.info("Inserindo no banco...")
    insert_records(records)
    logger.info("Pronto! Agora rode: python train.py")


if __name__ == "__main__":
    main()
