"""
Cliente para a API de Direções do OpenRouteService (ORS).
Substitui o Google Maps Distance Matrix API — completamente gratuito.

Limites do plano gratuito:
  - 2.000 requisições/dia
  - 40 requisições/minuto
  - Sem cartão de crédito

Cadastro gratuito em: https://openrouteservice.org/dev/#/signup
Documentação: https://openrouteservice.org/dev/#/api-docs/v2/directions
"""

import os
import logging
import requests

logger = logging.getLogger(__name__)

ORS_KEY = os.environ.get("ORS_API_KEY", "")

# Endpoint de direções de carro
DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/driving-car"


def fetch_traffic(origin: str, destination: str) -> dict:
    """
    Consulta o OpenRouteService Directions API e retorna duração e distância.

    Nota: o ORS não fornece dados de trânsito em tempo real (ao contrário do
    Google Maps). Para simular o impacto do trânsito, aplicamos um fator de
    congestionamento baseado no horário e nas condições climáticas coletadas
    separadamente. Isso é feito no módulo principal (main.py).

    Args:
        origin: "lat,lng" do ponto de origem
        destination: "lat,lng" do ponto de destino

    Returns:
        dict com duration (segundos), duration_in_traffic (segundos), distance (metros)
    """
    try:
        # ORS espera coordenadas no formato [lng, lat] (GeoJSON)
        origin_lat, origin_lng = map(float, origin.split(","))
        dest_lat, dest_lng = map(float, destination.split(","))

        headers = {
            "Authorization": ORS_KEY,
            "Content-Type": "application/json",
        }

        body = {
            "coordinates": [
                [origin_lng, origin_lat],
                [dest_lng, dest_lat],
            ],
            "instructions": False,
            "preference": "fastest",
            "units": "m",
        }

        resp = requests.post(DIRECTIONS_URL, json=body, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        segment = data["routes"][0]["summary"]
        duration_s = int(segment["duration"])   # segundos
        distance_m = int(segment["distance"])   # metros

        # ORS não tem trânsito em tempo real — o fator de congestionamento
        # é aplicado pelo coletor com base no horário e na chuva (main.py).
        return {
            "duration": duration_s,
            "duration_in_traffic": duration_s,  # ajustado no main.py
            "distance": distance_m,
        }

    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 429:
            logger.warning("Limite de requisições ORS atingido. Usando fallback.")
        else:
            logger.error(f"Erro HTTP ORS: {e}")
        return _fallback()

    except Exception as e:
        logger.error(f"Erro ao consultar OpenRouteService: {e}")
        return _fallback()


def _fallback() -> dict:
    """Retorna zeros em caso de falha para não interromper a coleta."""
    return {"duration": 0, "duration_in_traffic": 0, "distance": 0}
