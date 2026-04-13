"""
Feature engineering para o modelo de predição de atrasos.
Gera lag features, rolling stats e variáveis derivadas a partir
dos registros brutos do banco de dados.
"""

import pandas as pd
import numpy as np


FEATURE_COLS = [
    # Temporais
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    "is_rush_hour",
    # Climáticas
    "rain_mm",
    "temp_celsius",
    "humidity",
    "is_raining",
    # Lag features (janelas de 15min cada)
    "lag_15min",
    "lag_30min",
    "lag_60min",
    "lag_90min",
    # Estatísticas rolantes
    "rolling_mean_1h",
    "rolling_std_1h",
    "rolling_max_1h",
    # Histórico da mesma hora (semana anterior)
    "same_hour_last_week",
    # Razão de atraso atual
    "current_delay_ratio",
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recebe DataFrame bruto do banco e retorna DataFrame com
    todas as features e a coluna target.

    Target: `target_delayed` = 1 se a próxima leitura terá delay > 20%
    """
    df = df.copy()
    df = df.sort_values(["route_id", "collected_at"]).reset_index(drop=True)

    # Converte booleanos do postgres para int
    df["is_weekend"] = df["is_weekend"].astype(int)
    df["is_rush_hour"] = df["is_rush_hour"].astype(int)

    # Feature binária de chuva
    df["is_raining"] = (df["rain_mm"] > 0.5).astype(int)

    # Razão de atraso atual: quanto acima do tempo normal
    df["current_delay_ratio"] = df["duration_in_traffic"] / df["duration_seconds"].clip(lower=1)

    # Lag features por rota
    grp = df.groupby("route_id")["duration_in_traffic"]
    df["lag_15min"] = grp.shift(1)
    df["lag_30min"] = grp.shift(2)
    df["lag_60min"] = grp.shift(4)
    df["lag_90min"] = grp.shift(6)

    # Rolling stats da última hora (4 leituras de 15min)
    # Agrupamos por rota, fazemos rolling e voltamos para o índice original
    df["rolling_mean_1h"] = df.groupby("route_id")["duration_in_traffic"].rolling(window=4, min_periods=2).mean().reset_index(level=0, drop=True)
    df["rolling_std_1h"]  = df.groupby("route_id")["duration_in_traffic"].rolling(window=4, min_periods=2).std().reset_index(level=0, drop=True).fillna(0)
    df["rolling_max_1h"]  = df.groupby("route_id")["duration_in_traffic"].rolling(window=4, min_periods=2).max().reset_index(level=0, drop=True)

    # Média histórica da mesma hora, mesmo dia da semana (últimas 4 semanas)
    # Pegamos o valor da semana passada [shift(1)] e tiramos a média das 4 ocorrências anteriores
    df["same_hour_last_week"] = (
        df.groupby(["route_id", "day_of_week", "hour_of_day"])["duration_in_traffic"]
        .transform(lambda x: x.shift(1).rolling(window=4, min_periods=1).mean())
    )

    # Targets: nas próximas janelas (+15m, +30m, +60m), haverá atraso > 20%?
    df["target_15m"] = (
        df.groupby("route_id")["current_delay_ratio"]
        .shift(-1)
        .gt(1.20)
        .astype(int)
    )
    df["target_30m"] = (
        df.groupby("route_id")["current_delay_ratio"]
        .shift(-2)
        .gt(1.20)
        .astype(int)
    )
    df["target_60m"] = (
        df.groupby("route_id")["current_delay_ratio"]
        .shift(-4)
        .gt(1.20)
        .astype(int)
    )

    # Removemos apenas se faltar as features essenciais. 
    # Para o target, dropna será feito individualmente no treino para não perder dados de 15m se faltar 60m.
    return df.dropna(subset=FEATURE_COLS)


def get_feature_matrix(df: pd.DataFrame, target_col: str = "target_15m"):
    """Retorna X (features) e y (target) para treino."""
    df_feat = build_features(df)
    # Garante que temos o target para aquela linha
    df_feat = df_feat.dropna(subset=[target_col])
    
    X = df_feat[FEATURE_COLS]
    y = df_feat[target_col]
    return X, y
