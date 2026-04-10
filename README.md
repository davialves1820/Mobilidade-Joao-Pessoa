# 🚌 Mobilidade JP — Predição de Atrasos de Tráfego em João Pessoa, PB

> Desenvolvi um sistema de Machine Learning para prever gargalos de mobilidade em João Pessoa, PB.
> O sistema integra dados climáticos e de tráfego em tempo real para prever atrasos em corredores
> críticos da cidade, permitindo uma melhor gestão da frota urbana.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![XGBoost](https://img.shields.io/badge/ML-XGBoost-orange)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688)
![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B)
![Docker](https://img.shields.io/badge/Deploy-Docker-2496ED)
![Free APIs](https://img.shields.io/badge/APIs-100%25%20gratuitas-brightgreen)

---

## 📌 O problema

João Pessoa possui gargalos geográficos bem definidos: o corredor Mangabeira–Centro concentra
boa parte do tráfego da zona sul, e eventos climáticos (chuvas intensas, típicas do litoral nordestino)
alteram drasticamente a demanda e o tempo de deslocamento. Não há atualmente um sistema público
que combine dados de clima e tráfego para antecipar esses gargalos.

---

## 🆓 APIs utilizadas — todas gratuitas, sem cartão

| API | Substitui | Limite gratuito | Chave necessária? |
|-----|-----------|-----------------|-------------------|
| [OpenRouteService](https://openrouteservice.org) | Google Maps Distance Matrix | 2.000 req/dia | ✅ Sim (cadastro gratuito) |
| [Open-Meteo](https://open-meteo.com) | OpenWeatherMap | 10.000 req/dia | ❌ Não |

**Por que essa combinação funciona para este projeto?**

- A cada 15 minutos, o coletor faz **4 chamadas ao ORS** (uma por rota) + **1 ao Open-Meteo**.
  Isso resulta em **96 chamadas/dia ao ORS** — muito abaixo do limite de 2.000.
- O Open-Meteo é open-source, sem autenticação, com atualização horária dos modelos climáticos.
- Como o ORS não tem dados de trânsito em tempo real, aplicamos um **fator de congestionamento empírico**
  baseado no horário e na chuva. O modelo ML aprende a correção real com o tempo.

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────┐
│              Fontes de dados (gratuitas)             │
│  OpenRouteService (OSM)  │  Open-Meteo  │  SEMOB-JP │
└────────┬─────────────────┴──────┬────────┴───────────┘
         │                        │
         ▼                        ▼
┌─────────────────────────────────────────────────────┐
│     Coletor Python (APScheduler — a cada 15min)      │
│   + fator de congestionamento empírico por horário   │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│        PostgreSQL + TimescaleDB (série temporal)     │
└────────────────────────┬────────────────────────────┘
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
┌─────────────────────┐   ┌──────────────────────────┐
│  ml/train.py        │   │  FastAPI (REST /predict)  │
│  XGBoost + features │   │  Expõe predições          │
└─────────────────────┘   └──────────────┬───────────┘
                                         │
                                         ▼
                          ┌──────────────────────────┐
                          │  Streamlit Dashboard      │
                          │  Mapa folium + gráficos   │
                          └──────────────────────────┘
```

---

## 📊 Modelo de Machine Learning

**Algoritmo:** XGBoost Classifier com validação por TimeSeriesSplit (5 folds)

**Target:** Prediz se haverá atraso > 20% na próxima janela de 15 minutos

**Features principais:**
- Lag features: duração estimada nas últimas 15, 30, 60 e 90 minutos
- Rolling stats: média, desvio padrão e máximo da última hora
- Contexto temporal: hora do dia, dia da semana, horário de pico, fim de semana
- Clima: precipitação (mm), temperatura, umidade relativa (via Open-Meteo)
- Histórico da mesma hora na semana anterior

---

## 🗺️ Rotas monitoradas

| ID | Trecho | Relevância |
|----|--------|-----------|
| `mangabeira_centro` | Mangabeira Shopping → Centro | Principal corredor sul–centro |
| `epitacio_beira_rio` | Av. Epitácio Pessoa → Centro | Acesso à orla e Tambaú |
| `br230_mangabeira` | BR-230 → Mangabeira | Entrada sul da cidade |
| `altiplano_centro` | Altiplano Cabo Branco → Centro | Zona norte–leste |

---

## 🚀 Como rodar

### Pré-requisitos
- Docker e Docker Compose
- Chave gratuita do [OpenRouteService](https://openrouteservice.org/dev/#/signup) (cadastro leva 1 min)
- Open-Meteo: nenhuma configuração necessária

### 1. Configurar variáveis de ambiente

```bash
cp .env.example .env
# Edite o .env e coloque sua chave ORS_API_KEY
# Open-Meteo não precisa de chave — não há nada a configurar
```

### 2. Subir banco e coletor

```bash
docker compose up -d db
docker compose up -d collector
```

### 3. Acompanhar a coleta

```bash
docker compose logs -f collector
# Você verá logs como:
# Clima (Open-Meteo): Rain | 28.5°C | chuva=4.2mm | umidade=87%
# Mangabeira → Centro: base=18min → estimado=26min (+42%) 🔴 congestionado
```

### 4. Treinar o modelo (após 2–5 dias de coleta)

```bash
cd ml && pip install -r requirements.txt
python train.py
```

### 5. Subir API e dashboard

```bash
docker compose up --build
```

- **Dashboard:** http://localhost:8501
- **API docs:** http://localhost:8000/docs

---

## 📁 Estrutura do projeto

```
mobilidade-jp/
├── docker-compose.yml
├── .env.example            ← apenas ORS_API_KEY necessária
├── collector/
│   ├── main.py             ← Scheduler + fator de congestionamento
│   ├── db.py               ← PostgreSQL + TimescaleDB
│   └── apis/
│       ├── traffic.py      ← OpenRouteService (gratuito, OSM)
│       ├── weather.py      ← Open-Meteo (sem chave)
│       └── semob.py        ← Scraper SEMOB-JP + fallback
├── ml/
│   ├── features.py         ← Lag features + feature engineering
│   ├── train.py            ← XGBoost com TimeSeriesSplit
│   └── predict.py          ← Inferência
├── api/
│   ├── main.py             ← FastAPI REST
│   └── schemas.py
└── dashboard/
    └── app.py              ← Streamlit + mapa folium + Plotly
```

---

## 🔌 API — Endpoints principais

```
GET  /health                     → Status da API e do modelo
POST /predict                    → Predição de atraso para uma rota
GET  /routes/stats               → Estatísticas das últimas 24h
GET  /routes/{route_id}/history  → Histórico de uma rota
```

---

## 🧩 Próximos passos

- [ ] Integrar dados GTFS da SEMOB-JP quando disponíveis
- [ ] Adicionar modelo LSTM para sequências longas
- [ ] Alertas via Telegram quando severity = "alto"
- [ ] Deploy na nuvem (Railway ou Render — free tier)
- [ ] Calibrar o fator de congestionamento com dados reais de JP

---

## 👤 Autor

Desenvolvido por **[seu nome]** como projeto de portfólio em ciência de dados aplicada
à mobilidade urbana de João Pessoa, PB.
