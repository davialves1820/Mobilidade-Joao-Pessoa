"""
Scraper para dados da SEMOB-JP (Superintendência Executiva de Mobilidade Urbana).
Tenta capturar informações de linhas de ônibus do portal público.

Como usar:
    from apis.semob import fetch_lines
    linhas = fetch_lines()
"""

import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Portal público da Prefeitura de JP / SEMOB
SEMOB_URL = "https://transparencia.joaopessoa.pb.gov.br"

# Linhas prioritárias para monitoramento
PRIORITY_LINES = {
    "1500": "Circular Centro–Mangabeira",
    "5100": "Circular Sul",
    "3100": "Mangabeira–Centro (Epitácio)",
    "0700": "Tambaú–Centro",
}


def fetch_lines() -> list[dict]:
    """
    Tenta buscar informações de linhas no portal da SEMOB.
    Retorna lista de dicts com code, name, status.
    Fallback: retorna as linhas prioritárias com status desconhecido.
    """
    try:
        resp = requests.get(SEMOB_URL, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Tentativa de parse (adaptar conforme estrutura real do portal)
        rows = soup.select("table.linhas tr") or []
        lines = []
        for row in rows[1:]:  # pula header
            cols = row.find_all("td")
            if len(cols) >= 2:
                lines.append({
                    "code": cols[0].get_text(strip=True),
                    "name": cols[1].get_text(strip=True),
                    "status": "ok",
                })

        if lines:
            return lines

    except Exception as e:
        logger.warning(f"SEMOB scraping falhou: {e}. Usando fallback estático.")

    # Fallback: linhas manuais para não bloquear o pipeline
    return [
        {"code": code, "name": name, "status": "fallback"}
        for code, name in PRIORITY_LINES.items()
    ]


def fetch_gtfs_if_available() -> bool:
    """
    Verifica se há feed GTFS disponível no portal.
    GTFS é o padrão aberto para dados de transporte público.
    Retorna True se encontrar e salvar o arquivo.
    """
    gtfs_urls = [
        f"{SEMOB_URL}/gtfs/feed.zip",
        "https://dados.joaopessoa.pb.gov.br/gtfs/feed.zip",
    ]
    for url in gtfs_urls:
        try:
            resp = requests.head(url, timeout=5)
            if resp.status_code == 200:
                logger.info(f"GTFS encontrado em: {url}")
                # Download
                data = requests.get(url, timeout=30)
                with open("/tmp/semob_gtfs.zip", "wb") as f:
                    f.write(data.content)
                return True
        except Exception:
            continue
    logger.info("Feed GTFS não encontrado nos portais conhecidos.")
    return False
