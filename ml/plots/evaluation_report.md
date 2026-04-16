# Relatório Técnico de Performance do Modelo

Este documento contém a análise de performance hold-out (últimos 20% dos dados historicos).

## Horizonte: 15m
- **AUC-ROC**: 0.9386

### Relatório de Classificação:
```text
              precision    recall  f1-score   support

           0       0.90      0.98      0.94      4404
           1       0.93      0.72      0.81      1756

    accuracy                           0.90      6160
   macro avg       0.91      0.85      0.87      6160
weighted avg       0.91      0.90      0.90      6160

```

---

## Horizonte: 30m
- **AUC-ROC**: 0.9335

### Relatório de Classificação:
```text
              precision    recall  f1-score   support

           0       0.89      0.96      0.93      4408
           1       0.89      0.71      0.79      1752

    accuracy                           0.89      6160
   macro avg       0.89      0.84      0.86      6160
weighted avg       0.89      0.89      0.89      6160

```

---

## Horizonte: 60m
- **AUC-ROC**: 0.9320

### Relatório de Classificação:
```text
              precision    recall  f1-score   support

           0       0.91      0.94      0.92      4419
           1       0.84      0.75      0.79      1741

    accuracy                           0.89      6160
   macro avg       0.87      0.85      0.86      6160
weighted avg       0.89      0.89      0.89      6160

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
