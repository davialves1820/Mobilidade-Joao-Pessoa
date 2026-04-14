# 🚌 Mobilidade JP — Predictor

> Sistema de Inteligência Artificial para antecipar gargalos de tráfego em João Pessoa, PB.
> Este projeto utiliza a **TomTom Traffic API** para monitorar corredores críticos e modelos **XGBoost** para prever o trânsito com múltiplos horizontes de tempo (+15, +30 e +60 min).

![Python](https://img.shields.io/badge/Python-3.11-blue)
![XGBoost](https://img.shields.io/badge/ML-XGBoost-orange)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688)
![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B)
![Docker](https://img.shields.io/badge/Deploy-Docker-2496ED)

---

## 📌 Visão Geral

O **Mobilidade JP** vai além de um simples mapa de trânsito em tempo real. Enquanto ferramentas como o Google Maps mostram onde o trânsito *está* ruim agora, nosso sistema utiliza aprendizado de máquina para prever **onde ele estará ruim nos próximos 60 minutos**, permitindo antecipar congestionamentos causados por horários de pico ou chuvas intensas.

### ✨ Principais Funcionalidades
- **🤖 Previsão Multi-Horizonte**: IA treinada para prever o risco de atraso em 15, 30 e 60 minutos.
- **📈 Análise de Tendência**: Indicadores visuais que mostram se o trânsito está com tendência de piorar (🔺) ou melhorar (🔻).
- **🔮 Mapa do Futuro**: Controle deslizante que altera todo o visual da cidade para o estado projetado pela IA.
- **⚡ Monitoramento Real**: Integração direta com a API da TomTom e Open-Meteo (Clima).

---

## 🖼️ Demonstração

### Visão Geral do Dashboard
![Painel de Controle e Mapa](screenshots/dashboard_overview.png)

### Evolução do Atraso (Histórico)
![Gráfico de Evolução](screenshots/delay_evolution.png)

### Resumo de Desempenho (24h)
![Tabela de Resumo](screenshots/performance_summary.png)

## 🏗️ Arquitetura do Sistema

```mermaid
graph TD
    A[TomTom API - Trânsito] --> E[Coletor Python]
    B[Open-Meteo API - Clima] --> E
    E --> F[(TimescaleDB)]
    F --> G[ml/train.py - IA Multi-Target]
    G --> H1[Modelo +15m]
    G --> H2[Modelo +30m]
    G --> H3[Modelo +60m]
    H1 & H2 & H3 --> I[FastAPI Predict]
    I --> J[Streamlit Dashboard]
```

---

## 🔌 APIs Consumidas

O sistema integra dados de múltiplas fontes para alimentar o modelo de inteligência artificial:

1.  **[TomTom Traffic API](https://developer.tomtom.com/traffic-api)**:
    - **Finalidade**: Fornece dados reais de tempo de percurso, velocidade média e níveis de congestionamento.
    - **Uso**: É a fonte principal para a variável alvo (atraso real) e para o monitoramento em tempo real dos corredores.
2.  **[Open-Meteo API](https://open-meteo.com/)**:
    - **Finalidade**: Coleta condições climáticas (chuva, temperatura, umidade) em João Pessoa.
    - **Uso**: A chuva é um fator crítico para o trânsito da cidade; esses dados ajudam a IA a entender como o clima impactará o tráfego nos próximos minutos.

---

## 🚀 Como Rodar

### 1. Pré-requisitos
- Docker e Docker Compose.
- Chave de API da [TomTom Developers](https://developer.tomtom.com/).

### 2. Configuração
Crie um arquivo `.env` na raiz:
```bash
TOMTOM_API_KEY=sua_chave_aqui
DATABASE_URL=postgresql://postgres:davi.2005@db:5432/monitoramento
```

### 3. Execução
```bash
docker compose up --build -d
```
Serviços disponíveis:
- **Dashboard**: [http://localhost:8501](http://localhost:8501)
- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧠 Treinamento da IA

O sistema utiliza modelos **XGBoost** especializados para cada janela de tempo. Para atualizar os modelos com os dados mais recentes coletados:

```bash
# Executa o treinamento multi-horizonte via Docker
docker compose exec api python ml/train.py
```
*Isso gerará os arquivos `model_15m.pkl`, `model_30m.pkl` e `model_60m.pkl` na pasta da API.*

---

## 🗺️ Rotas Monitoradas
O sistema foca nos 5 eixos principais de João Pessoa:
1.  **Mangabeira Mall → Centro** (Principal eixo Sul)
2.  **Av. Epitácio Pessoa → Centro** (Corredor comercial)
3.  **BR-230 → Mangabeira** (Fluxo logístico)
4.  **Altiplano → Centro** (Zona leste)
5.  **Bessa → Centro** (Zona norte)

---

## 📁 Estrutura do Projeto
- `collector/`: Scraper de tráfego e clima (APScheduler).
- `ml/`: Engenharia de variáveis e script de treinamento.
- `api/`: Endpoints FastAPI para servir as predições.
- `dashboard/`: Interface Streamlit com mapas Folium e gráficos Plotly.
