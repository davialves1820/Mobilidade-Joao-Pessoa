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

