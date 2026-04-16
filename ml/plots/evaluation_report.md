# Relatório Técnico de Performance do Modelo

Este documento contém a análise de performance hold-out (últimos 20% dos dados historicos).

## Horizonte: 15m
- **AUC-ROC**: 0.9834

### Relatório de Classificação:
```text
              precision    recall  f1-score   support

           0       0.94      0.97      0.95      1280
           1       0.94      0.90      0.92       798

    accuracy                           0.94      2078
   macro avg       0.94      0.93      0.94      2078
weighted avg       0.94      0.94      0.94      2078

```

---

## Horizonte: 30m
- **AUC-ROC**: 0.9786

### Relatório de Classificação:
```text
              precision    recall  f1-score   support

           0       0.93      0.95      0.94      1281
           1       0.92      0.88      0.90       797

    accuracy                           0.92      2078
   macro avg       0.92      0.92      0.92      2078
weighted avg       0.92      0.92      0.92      2078

```

---

## Horizonte: 60m
- **AUC-ROC**: 0.9809

### Relatório de Classificação:
```text
              precision    recall  f1-score   support

           0       0.92      0.97      0.94      1275
           1       0.95      0.86      0.90       803

    accuracy                           0.93      2078
   macro avg       0.93      0.91      0.92      2078
weighted avg       0.93      0.93      0.93      2078

```

---

## Legenda dos Termos

### Colunas:
- **Precision (Precisão):** Indica a qualidade das predições positivas. Das vezes que o modelo previu "Atraso", qual o percentual de acerto real?
- **Recall (Revocação):** Indica a capacidade do modelo de encontrar os casos reais. De todos os "Atrasos" que realmente aconteceram, quantos o modelo conseguiu detectar?
- **F1-Score:** Uma média entre Precisão e Recall. É a melhor métrica única para avaliar modelos com dados desbalanceados.
- **Support (Suporte):** O número real de ocorrências de cada classe no conjunto de dados testado.

### Linhas:
- **0:** Classe representando Trânsito Livre (Sem Atraso significativo).
- **1:** Classe representando Trânsito com Atraso (Congestionamento).
- **Accuracy (Acurácia):** O percentual total de acertos do modelo (predições corretas divididas pelo total de predições).
- **Macro Avg:** Média simples das métricas entre as classes, tratando ambas com a mesma importância.
- **Weighted Avg:** Média das métricas ponderada pelo suporte, dando mais peso para a classe que aparece com mais frequência.