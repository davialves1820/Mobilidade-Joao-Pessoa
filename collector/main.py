"""
Coletor principal — roda a cada 15 minutos via APScheduler.
Captura dados de tráfego (OpenRouteService) e clima (Open-Meteo)
e salva no PostgreSQL.

APIs usadas — todas gratuitas, sem cartão:
  - OpenRouteService: roteamento/distância (2.000 req/dia grátis)
  - Open-Meteo:       clima em tempo real (sem chave, sem limite prático)
"""

import logging
import math
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

load_dotenv()

from apis.traffic import fetch_traffic
from apis.weather import fetch_weather
from db import init_db, save_record

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("coletor")

# ──────────────────────────────────────────────
# Rotas monitoradas em João Pessoa
# ──────────────────────────────────────────────
ROUTES = [
    {
        "id": "mangabeira_centro",
        "label": "Mangabeira Shopping → Centro",
        "origin": "-7.1695,-34.8468",
        "destination": "-7.1153,-34.8641",
    },
    {
        "id": "epitacio_beira_rio",
        "label": "Av. Epitácio Pessoa → Centro",
        "origin": "-7.1285,-34.8309",
        "destination": "-7.1153,-34.8641",
    },
    {
        "id": "br230_mangabeira",
        "label": "BR-230 → Mangabeira",
        "origin": "-7.1770,-34.8360",
        "destination": "-7.1695,-34.8468",
    },
    {
        "id": "bessa_centro",
        "label": "Bessa → Centro",
        "origin": "-7.0870,-34.8350",
        "destination": "-7.1150,-34.8630",
    },
    {
        "id": "altiplano_centro",
        "label": "Altiplano → Centro",
        "origin": "-7.1350,-34.8250", # Altiplano
        "destination": "-7.1153,-34.8641", # Centro
    },
]

scheduler = BlockingScheduler(timezone="America/Recife")


def _apply_congestion_factor(duration_s: int, weather: dict) -> int:
    """
    O OpenRouteService não tem dados de trânsito em tempo real.
    Aplicamos um fator empírico de congestionamento baseado em:
      - Horário de pico (manhã e tarde)
      - Chuva (aumenta o tempo significativamente em JP)
      - Dia da semana

    Este fator alimenta a feature `duration_in_traffic` do modelo ML,
    que aprende a correlação real ao longo do tempo.

    Referência de calibração para JP:
      - Hora de pico sem chuva: +25 a +40%
      - Hora de pico com chuva forte: +60 a +90%
      - Fora do pico, dia de semana: +5 a +15%
      - Fim de semana: -5 a +10%
    """
    now = datetime.now()
    hour = now.hour
    weekday = now.weekday()  # 0=seg, 6=dom

    factor = 1.0

    # Pico da manhã (6h–9h)
    if 6 <= hour < 9:
        factor += 0.35

    # Pico da tarde (17h–20h)
    elif 17 <= hour < 20:
        factor += 0.40

    # Horário intermediário dia útil
    elif weekday < 5 and 9 <= hour < 17:
        factor += 0.10

    # Fim de semana — trânsito mais leve
    elif weekday >= 5:
        factor -= 0.05

    # Impacto da chuva (João Pessoa: chuvas intensas afetam muito o trânsito)
    rain_mm = weather.get("rain_1h", 0)
    if rain_mm > 10:
        factor += 0.45   # chuva forte
    elif rain_mm > 3:
        factor += 0.25   # chuva moderada
    elif rain_mm > 0.5:
        factor += 0.10   # garoa

    return int(duration_s * factor)


def collect_all():
    """Coleta dados de todas as rotas e salva no banco."""
    logger.info(f"=== Início da coleta — {datetime.now().strftime('%H:%M')} ===")

    # Open-Meteo: 1 chamada para toda a cidade
    weather = fetch_weather()
    logger.info(
        f"Clima (Open-Meteo): {weather['weather_main']} | "
        f"{weather['temp']}°C | "
        f"chuva={weather['rain_1h']}mm | "
        f"umidade={weather['humidity']}%"
    )

    for route in ROUTES:
        try:
            # OpenRouteService: 1 chamada por rota
            traffic = fetch_traffic(route["origin"], route["destination"])

            if traffic["duration"] == 0:
                logger.warning(f"Dados zerados para {route['id']}, pulando.")
                continue

            # Aplica fator de congestionamento empírico
            duration_in_traffic = _apply_congestion_factor(
                traffic["duration"], weather
            )
            traffic["duration_in_traffic"] = duration_in_traffic

            record = {
                "route_id": route["id"],
                "duration_seconds": traffic["duration"],
                "duration_in_traffic": traffic["duration_in_traffic"],
                "distance_meters": traffic["distance"],
                "rain_mm": weather["rain_1h"],
                "temp_celsius": weather["temp"],
                "humidity": weather["humidity"],
                "weather_main": weather["weather_main"],
            }
            save_record(record)

            delay_ratio = traffic["duration_in_traffic"] / max(traffic["duration"], 1)
            status = (
                "🔴 congestionado" if delay_ratio > 1.3
                else "🟡 lento" if delay_ratio > 1.1
                else "🟢 livre"
            )
            logger.info(
                f"{route['label']}: "
                f"base={traffic['duration']//60}min → "
                f"estimado={traffic['duration_in_traffic']//60}min "
                f"(+{int((delay_ratio - 1) * 100)}%) {status}"
            )

        except Exception as e:
            logger.error(f"Erro ao coletar {route['id']}: {e}", exc_info=True)

    logger.info("=== Coleta concluída ===\n")


@scheduler.scheduled_job("interval", minutes=15, id="coleta_principal")
def scheduled_collect():
    collect_all()


if __name__ == "__main__":
    logger.info("Inicializando banco de dados...")
    init_db()

    logger.info("Primeira coleta imediata...")
    collect_all()

    logger.info("Scheduler iniciado — coletando a cada 15 minutos.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Coletor encerrado.")
