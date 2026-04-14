"""
Dashboard Streamlit — Mobilidade Urbana de João Pessoa, PB
Visualiza predições de atraso em tempo real com mapa interativo folium.
"""

import os
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import folium
import streamlit as st
from streamlit_folium import st_folium
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

API_URL = os.environ.get("API_URL", "http://localhost:8000")

# ─────────────────────────────────────────────
# Configuração da página
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Mobilidade JP",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .metric-card {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 16px 20px;
        border-left: 4px solid #0066cc;
        margin-bottom: 12px;
        position: relative;
        color: #1a1a1a !important; /* Força cor escura para legibilidade */
    }
    .metric-card strong, .metric-card span, .metric-card b {
        color: #1a1a1a !important;
    }
    .alert-high   { border-left-color: #dc3545; background: #fff5f5; }
    .alert-medium { border-left-color: #fd7e14; background: #fff8f0; }
    .alert-low    { border-left-color: #28a745; background: #f4fff6; }
    .trend-icon {
        position: absolute;
        top: 10px;
        right: 15px;
        font-size: 1.2em;
        opacity: 0.8;
    }
    .stMetric { background: #f0f4ff; border-radius: 10px; padding: 10px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Coordenadas das rotas em João Pessoa
# ─────────────────────────────────────────────
ROUTES_INFO = {
    "mangabeira_centro": {
        "label": "Mangabeira Shopping → Centro",
        "coords": [(-7.1695, -34.8468), (-7.1153, -34.8641)],
        "color": "#0066cc",
    },
    "epitacio_beira_rio": {
        "label": "Av. Epitácio Pessoa → Centro",
        "coords": [(-7.1285, -34.8309), (-7.1153, -34.8641)],
        "color": "#9933cc",
    },
    "br230_mangabeira": {
        "label": "BR-230 → Mangabeira",
        "coords": [(-7.1770, -34.8360), (-7.1695, -34.8468)],
        "color": "#cc6600",
    },
    "altiplano_centro": {
        "label": "Altiplano → Centro",
        "coords": [(-7.1350, -34.8250), (-7.1153, -34.8641)],
        "color": "#00997a",
    },
    "bessa_centro": {
        "label": "Bessa → Centro",
        "coords": [(-7.0870, -34.8350), (-7.1150, -34.8630)],
        "color": "#00BCD4",
    },
}

SEVERITY_COLORS = {"alto": "#dc3545", "médio": "#fd7e14", "baixo": "#28a745"}
SEVERITY_ICONS  = {"alto": "🔴", "médio": "🟡", "baixo": "🟢"}
TREND_ICONS = {
    "increasing": "📈 piorando",
    "decreasing": "📉 melhorando",
    "stable": "➡️ estável"
}


# ─────────────────────────────────────────────
# Funções de dados
# ─────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_stats():
    try:
        r = requests.get(f"{API_URL}/routes/stats", timeout=5)
        r.raise_for_status()
        return {s["route_id"]: s for s in r.json()}
    except Exception:
        return {}


@st.cache_data(ttl=60)
def fetch_history(route_id: str = "", hours: int = 6):
    try:
        if route_id:
            url = f"{API_URL}/routes/{route_id}/history"
        else:
            url = f"{API_URL}/history"
            
        r = requests.get(url, params={"hours": hours}, timeout=5)
        r.raise_for_status()
        data = r.json()
        
        # O endpoint global retorna lista direta, o específico retorna um objeto com 'records'
        records = data["records"] if isinstance(data, dict) and "records" in data else data
        df = pd.DataFrame(records)
        
        if not df.empty:
            df["collected_at"] = pd.to_datetime(df["collected_at"].astype(str).str[:19])
            df["collected_at"] = df["collected_at"].dt.tz_localize("UTC").dt.tz_convert("America/Fortaleza")
        return df
    except Exception as e:
        st.error(f"Erro ao buscar histórico: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=30)
def fetch_health():
    try:
        r = requests.get(f"{API_URL}/health", timeout=3)
        return r.json()
    except Exception:
        return {"status": "offline", "model_loaded": False, "db_connected": False}



@st.cache_data(ttl=60)
def fetch_prediction(route_id: str):
    try:
        r = requests.get(f"{API_URL}/routes/{route_id}/predict", timeout=5)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception:
        return None


# ─────────────────────────────────────────────
# Layout principal
# ─────────────────────────────────────────────
st.title("🚌 Mobilidade Urbana — João Pessoa, PB")
local_time = datetime.now(timezone.utc) - pd.Timedelta(hours=3)
st.caption(f"Atualizado em: {local_time.strftime('%d/%m/%Y %H:%M:%S')} (Horário Local) | Dados a cada 15 min")

# Status da API na barra lateral
with st.sidebar:
    st.header("⚙️ Painel de controle")
    health = fetch_health()
    status_color = "🟢" if health["status"] == "ok" else ("🟡" if health["status"] == "degraded" else "🔴")
    st.markdown(f"**Status da API:** {status_color} {health['status'].upper()}")
    st.markdown(f"**Modelo ML:** {'✅' if health.get('model_loaded') else '❌ não carregado'}")
    st.markdown(f"**Banco de dados:** {'✅' if health.get('db_connected') else '❌ desconectado'}")

    st.divider()
    st.subheader("🔮 Previsão Futura")
    horizon_map = {"Agora (+15m)": "15m", "Em 30 min": "30m", "Em 1 hora": "60m"}
    selected_horizon_label = st.radio(
        "Visualizar trânsito em:",
        options=list(horizon_map.keys()),
        index=0,
        help="Altera o mapa e os cards para mostrar a probabilidade de atraso no futuro."
    )
    horizon_key = horizon_map[selected_horizon_label]

    st.divider()
    st.subheader("🗺️ Configurações do mapa")
    map_style = st.selectbox(
        "Estilo do mapa",
        ["OpenStreetMap", "CartoDB positron", "CartoDB dark_matter"],
        index=1,
    )
    hours_back = st.slider("Histórico (horas)", min_value=1, max_value=24, value=6)

    st.divider()

    if st.button("🔄 Atualizar dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ─────────────────────────────────────────────
# Métricas de predição no topo
# ─────────────────────────────────────────────
st.subheader("📡 Predições de Atraso (IA)")
stats = fetch_stats()

cols = st.columns(len(ROUTES_INFO))
predictions = {}

for col, (route_id, info) in zip(cols, ROUTES_INFO.items()):
    pred = fetch_prediction(route_id)
    predictions[route_id] = pred
    
    with col:
        if pred and "forecasts" in pred:
            f_data = pred["forecasts"].get(horizon_key, pred)
            prob_pct = int(f_data["probability"] * 100)
            severity = f_data["severity"]
            icon = SEVERITY_ICONS[severity]
            trend = pred.get("trend", "stable")
            trend_icon = "🔺" if trend == "increasing" else ("🔻" if trend == "decreasing" else "🔹")
            
            st.markdown(
                f"""<div class="metric-card alert-{severity}">
                <div class="trend-icon" title="Previsão para 60 min: {trend}">{trend_icon}</div>
                <strong>{icon} {info['label']}</strong><br>
                <span style="font-size:1.6em;font-weight:bold">{prob_pct}%</span>
                <span style="font-size:0.8em;color:#666"> de risco</span><br>
                <span style="font-size:0.8em">Horizonte: <b>+{horizon_key}</b></span>
                </div>""",
                unsafe_allow_html=True,
            )
        elif pred: # Fallback para API antiga
            prob_pct = int(pred["delay_probability"] * 100)
            severity = pred["severity"]
            st.markdown(
                f"""<div class="metric-card alert-{severity}">
                <strong>{SEVERITY_ICONS[severity]} {info['label']}</strong><br>
                <span style="font-size:1.8em;font-weight:bold">{prob_pct}%</span>
                </div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""<div class="metric-card" style="border-left: 5px solid #ccc">
                <strong>⏳ {info['label']}</strong><br>
                <span style="font-size:1.2em;color:#999">Sem dados</span>
                </div>""",
                unsafe_allow_html=True,
            )

# ─────────────────────────────────────────────
# Mapa interativo de João Pessoa
# ─────────────────────────────────────────────
col_map, col_viz = st.columns([1.5, 1])

with col_map:
    st.subheader(f"📍 Mapa de Fluidez ({selected_horizon_label})")
    m = folium.Map(location=[-7.1150, -34.8500], zoom_start=13, tiles=map_style)
    
    for route_id, info in ROUTES_INFO.items():
        pred = predictions.get(route_id)
        if pred:
            # Usa os dados do horizonte selecionado
            f_data = pred.get("forecasts", {}).get(horizon_key, pred)
            severity = f_data.get("severity", "baixo")
            prob = f_data.get("probability", 0.1)
            
            color = SEVERITY_COLORS.get(severity, "#28a745")
            folium.PolyLine(
                locations=info["coords"], color=color, weight=5, opacity=0.8,
                tooltip=f"{info['label']}: {int(prob*100)}% risco (+{horizon_key})"
            ).add_to(m)
            
    st_folium(m, height=400, width=None, use_container_width=True)

with col_viz:
    st.subheader("📊 Ranking de Atraso")
    # Calcula atraso relativo médio
    ranking_items = []
    for r_id, r_info in ROUTES_INFO.items():
        s = stats.get(r_id, {})
        if s:
            avg_traffic = s.get("avg_duration_traffic") or 0
            avg_base = s.get("avg_duration_seconds") or 0
            ext_min = (avg_traffic - avg_base) / 60
            ranking_items.append({
                "Rota": r_info["label"],
                "Minutos Extras": round(ext_min if ext_min > 0 else 0, 1)
            })
    
    if ranking_items:
        df_rank = pd.DataFrame(ranking_items).sort_values("Minutos Extras", ascending=False)
        fig_rank = px.bar(
            df_rank, x="Minutos Extras", y="Rota", orientation='h',
            labels={"Minutos Extras": "Atraso Médio (min)"},
            color="Minutos Extras", color_continuous_scale="Reds"
        )
        fig_rank.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=10))
        st.plotly_chart(fig_rank, use_container_width=True)
    else:
        st.info("Coletando dados para o ranking...")

# Legenda
st.markdown(f"""
**Legenda (Previsão {selected_horizon_label}):** 🔴 Alto risco (>70%) &nbsp;|&nbsp; 🟡 Médio (40–70%) &nbsp;|&nbsp; 🟢 Baixo (<40%)
&nbsp; · Tendência (60 min): 🔺 Piorando &nbsp; 🔻 Melhorando &nbsp; 🔹 Estável
""")

# ─────────────────────────────────────────────
# Gráfico de histórico da rota selecionada
# ─────────────────────────────────────────────
st.subheader("📈 Evolução do Atraso (Minutos Extras)")
# Pega histórico global para comparar rotas
df_all = fetch_history("", hours=hours_back) 

if not df_all.empty:
    df_all["delay_min"] = (df_all["duration_in_traffic"] - df_all["duration_seconds"]) / 60
    df_all["route_name"] = df_all["route_id"].map(lambda x: ROUTES_INFO.get(x, {}).get("label", x))
    
    fig_trend = px.line(
        df_all, x="collected_at", y="delay_min", color="route_name",
        labels={"delay_min": "Atraso (min)", "collected_at": "Horário"},
        line_shape="spline", template="plotly_white", markers=True
    )
    fig_trend.update_layout(margin=dict(l=0, r=0, t=10, b=10), legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig_trend, use_container_width=True)
else:
    st.info("Sem dados históricos para o período.")

st.subheader("📋 Resumo de Desempenho (24h)")
if stats:
    summary = []
    for r_id, r_info in ROUTES_INFO.items():
        s = stats.get(r_id, {})
        avg_traffic = s.get("avg_duration_traffic") or 0
        avg_base = s.get("avg_duration_seconds") or 1
        avg_delay = ((avg_traffic / avg_base) - 1) * 100
        summary.append({
            "Rota": r_info["label"],
            "Tempo Médio": f"{round(s.get('avg_duration_traffic', 0)/60, 1)} min",
            "Atraso Médio": f"{round(avg_delay, 1)}%",
            "Pior Cenário": f"{round((s.get('max_delay_ratio', 1)-1)*100, 1)}%",
            "Situação": "🔴 Crítica" if avg_delay > 40 else ("🟡 Alerta" if avg_delay > 20 else "🟢 Fluindo")
        })
    st.dataframe(pd.DataFrame(summary), use_container_width=True, hide_index=True)
else:
    st.info("Estatísticas disponíveis após a primeira hora de coleta.")

st.divider()
st.caption(
    "Modelo XGBoost treinado em dados locais de João Pessoa, PB · "
    f"API: {API_URL}"
)
