"""
Cliente para a API Open-Meteo — dados climáticos de João Pessoa, PB.
100% gratuito, sem cadastro e sem chave de API.

Limites: 10.000 req/dia (uso justo). Para este projeto coletando a cada 15min,
usamos no máximo 96 req/dia — bem dentro do limite.

Documentação: https://open-meteo.com/en/docs
"""

import logging
import requests

logger = logging.getLogger(__name__)

# Coordenadas do centro de João Pessoa
JP_LAT = -7.1195
JP_LON = -34.8450

# Endpoint de previsão atual — sem autenticação
BASE_URL = "https://api.open-meteo.com/v1/forecast"

# Mapeamento dos códigos WMO de clima para texto legível
WMO_CODES = {
    0: "Clear",
    1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
    45: "Fog", 48: "Fog",
    51: "Drizzle", 53: "Drizzle", 55: "Drizzle",
    61: "Rain", 63: "Rain", 65: "Heavy Rain",
    71: "Snow", 73: "Snow", 75: "Heavy Snow",
    80: "Rain Showers", 81: "Rain Showers", 82: "Heavy Rain Showers",
    95: "Thunderstorm", 96: "Thunderstorm", 99: "Thunderstorm",
}


def fetch_weather() -> dict:
    """
    Retorna condições climáticas atuais em João Pessoa via Open-Meteo.
    Sem chave de API — chamada direta ao endpoint público.

    Returns:
        dict com temp, humidity, rain_1h, weather_main
    """
    params = {
        "latitude": JP_LAT,
        "longitude": JP_LON,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "rain",
            "weather_code",
            "wind_speed_10m",
        ],
        "timezone": "America/Recife",
        "forecast_days": 1,
    }

    try:
        resp = requests.get(BASE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        current = data["current"]

        wmo_code = current.get("weather_code", 0)
        weather_main = WMO_CODES.get(wmo_code, "Unknown")

        return {
            "temp": current["temperature_2m"],
            "humidity": current["relative_humidity_2m"],
            "rain_1h": current.get("rain", 0.0) or 0.0,
            "weather_main": weather_main,
            "wind_speed": current.get("wind_speed_10m", 0.0),
            "wmo_code": wmo_code,
        }

    except requests.RequestException as e:
        logger.error(f"Erro ao consultar Open-Meteo: {e}")
        # Fallback com valores típicos de JP para não interromper a coleta
        return {
            "temp": 28.0,
            "humidity": 75,
            "rain_1h": 0.0,
            "weather_main": "Unknown",
            "wind_speed": 0.0,
            "wmo_code": 0,
        }
