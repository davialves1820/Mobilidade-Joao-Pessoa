"""
Cliente para a API de Direções da TomTom (Traffic API).
Substitui o determinismo sintético para buscar tráfego nativamente real na cidade.

Acesso: 2.500 requisições/dia grátis.
"""

import os
import logging
import requests

logger = logging.getLogger(__name__)

TOMTOM_KEY = os.environ.get("TOMTOM_API_KEY", "")

def fetch_traffic(origin: str, destination: str) -> dict:
    """
    Consulta a API TomTom Routing v8/v5 com suporte a tráfego nativo.
    
    Args:
        origin: "lat,lng" do ponto de origem
        destination: "lat,lng" do ponto de destino
    """
    if not TOMTOM_KEY:
        logger.warning("TOMTOM_API_KEY ausente.")
        return _fallback()

    try:
        # TomTom usa formato lat,lng:long,lat (na verdade parece ser lat,lng:lat,lng no teste realizado)
        tomtom_locations = f"{origin}:{destination}"

        # Parâmetros vitais: computeTravelTimeFor=all traz os dados ideais (sem tráfego) e reais (com tráfego)
        url = f"https://api.tomtom.com/routing/1/calculateRoute/{tomtom_locations}/json"
        params = {
            "key": TOMTOM_KEY,
            "traffic": "true",
            "computeTravelTimeFor": "all"
        }

        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        segment = data["routes"][0]["summary"]
        
        # noTrafficTravelTimeInSeconds: Duração ideal / base
        # travelTimeInSeconds: Duração real devido ao trânsito / clima
        duration_s = int(segment.get("noTrafficTravelTimeInSeconds", segment.get("travelTimeInSeconds", 0)))
        duration_in_traffic = int(segment.get("travelTimeInSeconds", duration_s))
        distance_m = int(segment.get("lengthInMeters", 0))

        return {
            "duration": duration_s,
            "duration_in_traffic": duration_in_traffic,
            "distance": distance_m,
        }

    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 429:
            logger.warning("Limite de requisições TomTom atingido.")
        else:
            logger.error(f"Erro HTTP TomTom: {e.response.text if e.response else e}")
        return _fallback()

    except Exception as e:
        logger.error(f"Erro ao consultar TomTom: {e}")
        return _fallback()

def _fallback() -> dict:
    """Retorna zeros globais em caso de falha."""
    return {"duration": 0, "duration_in_traffic": 0, "distance": 0}
