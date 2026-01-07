# Guida alle metriche esposte

## 📊 Metriche dell'API Serving (FastAPI)

### Metriche di Traffic e Performance
- **`app_requests_total`** (Counter): Conteggio totale delle richieste a `/predict`. 
  - Utile per monitorare il volume di utilizzo nel tempo
  - Incrementato per ogni richiesta (successo o fallimento)

- **`app_errors_total`** (Counter): Conteggio totale degli errori durante l'inferenza.
  - Se cresce in parallelo alle richieste (`app_requests_total`), la qualità del servizio sta degradando
  - Verificare i log per identificare cause di errore

- **`app_request_latency_seconds`** (Histogram): Latenza end-to-end del `/predict` endpoint.
  - Traccia la durata completa da richiesta a risposta
  - In Grafana i pannelli p50/p90 usano:
    ```promql
    histogram_quantile(0.5, sum(rate(app_request_latency_seconds_bucket[5m])) by (le))  # p50 (mediana)
    histogram_quantile(0.9, sum(rate(app_request_latency_seconds_bucket[5m])) by (le))  # p90
    ```
  - **Perché p50/p90?** La media nasconde code lunghe. P50 mostra la latenza tipica, P90 cattura gli outlier che impattano l'esperienza utente.
  - **Valori attesi**: dopo warm-up, p50 < 500ms, p90 < 2s (dipende da hardware)

### Metriche di Sentiment
- **`app_sentiment_predictions_total`** (Counter with label `sentiment_label`): Conteggio delle predizioni per etichetta sentiment.
  - Labels: `sentiment_label ∈ {positive, neutral, negative}`
  - Esempio query Grafana per distribuzione:
    ```promql
    sum(rate(app_sentiment_predictions_total[5m])) by (sentiment_label)
    ```
  - **Utilità**: Permette di monitorare se il sentiment della community sta cambiando nel tempo
  - Se il `positive` crolla improvvisamente, potrebbe indicare un problema reputazionale che il DAG di drift non ha ancora catturato
  
### Monitoraggio Data Drift
- **`data_drift_flag`** (Gauge, 0/1): Segnale binario di data drift.
  - Inizializzato a 0 all'avvio della app
  - Aggiornato dal DAG Airflow via Pushgateway quando esegue la drift detection
  - **Valore 0**: nessun drift, dati coerenti con baseline
  - **Valore 1**: drift rilevato, trigger automatico del retraining

---

## 🤖 Metriche del Modello (da Airflow)

Dopo ogni run del task `evaluate_and_promote` nel DAG, vengono pushate a Prometheus le metriche di performance del modello:

- **`model_f1_score`** (Gauge with labels `model_name`, `model_version`): F1-score macro (media tra le 3 classi).
  - Range: 0.0–1.0
  - Calcolato su `data/holdout.csv` durante la fase di valutazione
  - Traccia come la qualità del modello evolve attraverso le versioni
  - **Alert suggerito**: Se scende sotto 0.75, investigare possibile data shift

- **`model_accuracy`** (Gauge with labels `model_name`, `model_version`): Accuracy globale.
  - Range: 0.0–1.0
  - Percentuale di predizioni corrette su tutto il dataset di valutazione
  - Utile come metrica complementare a F1 (soprattutto se le classi sono sbilanciate)

**Come vengono generate:**
1. DAG esegue `src.models.evaluate` con il nuovo modello
2. Evaluate calcola F1 e accuracy su holdout set
3. Se promuove a Production, DAG chiama `src.monitoring.push_model_metrics`
4. Metriche vengono pushate al Pushgateway con `job=model_performance`
5. Prometheus scrappa il Pushgateway e rende disponibile le metriche a Grafana

---

## 🔄 Flusso Prometheus/Pushgateway/Grafana

```
┌──────────────────────────┐
│  FastAPI App             │
│  - /predict endpoint    │ ──── Espone su /metrics (scrape ogni 15s) ───┐
│  - Metriche API         │                                              │
│  - app_sentiment_*      │                                              │
└──────────────────────────┘                                             │
                                                                          │
┌──────────────────────────┐                                             │
│  Airflow DAG             │                                             │
│  - evaluate_and_promote │ ──── Push model_f1_score, accuracy ────┐   │
│  - compute_drift        │      al Pushgateway (porta 9091)       │   │
│  - push_model_metrics   │                                        │   │
└──────────────────────────┘                                       │   │
                                                                   │   │
                                         ┌─────────────────────────▼───▼─────┐
                                         │   Prometheus (port 9090)          │
                                         │   - Scrappa app:/metrics          │
                                         │   - Scrappa pushgateway:9091      │
                                         │   - Fonde tutte le metriche       │
                                         └─────────────────┬──────────────────┘
                                                           │
                                                           │ Query (ogni 10s)
                                                           │
                                         ┌─────────────────▼──────────────────┐
                                         │   Grafana (port 3000)              │
                                         │   - Dashboard: MLOps – Sentiment   │
                                         │     Analysis Monitoring            │
                                         │   - Panels: Traffic, Sentiment,    │
                                         │     Performance, Drift            │
                                         └────────────────────────────────────┘
```

**Step-by-step:**
1. **FastAPI app**: Espone metriche Prometheus su `/metrics` in formato standard (Prometheus text format)
   - Prometheus scrappa questo endpoint ogni 15 secondi (job `app`)
   - Metriche include: richieste, errori, latenza, sentiment predictions

2. **Airflow DAG**: Durante il run di retraining, il task `evaluate_and_promote` 
   - Calcola F1/accuracy nuovo modello
   - Chiama `src.monitoring.push_model_metrics` per pushare le metriche
   - Le metriche vengono inviate al **Pushgateway** (porta 9091)

3. **Pushgateway**: Riceve le metriche e le espone per Prometheus
   - Prometheus ha un job dedicato per scrappare il Pushgateway
   - Unisce le metriche dal Pushgateway con quelle dall'app

4. **Grafana**: Legge tutte le metriche da Prometheus
   - Dashboard `MLOps – Sentiment Analysis Monitoring` visualizza:
     - Request rate e error rate
     - Latency percentili
     - Sentiment distribution (pie chart)
     - Model performance (F1 & accuracy timeline)
     - Data drift flag timeline
   - Auto-refresh ogni 10 secondi

---

## 📈 Pannelli Principali del Dashboard Grafana

### 1. **Request Rate** (`📊 API Request Rate`)
- Query: `rate(app_requests_total[1m])`
- **Cosa guardare:**
  - Se è piatto → non c'è traffico (possibile outage)
  - Se sale improvvisamente → burst di traffico
  - Se cala drasticamente → possibile downtime o problem nell'app
- **Target sano**: Dipende dal use case, ma dovrebbe essere consistente

### 2. **Error Rate** (`⚠️ API Error Rate`)
- Query: `rate(app_errors_total[1m]) / rate(app_requests_total[1m]) * 100`
- **Cosa guardare:**
  - < 0.5% è buono
  - 0.5% – 2% è accettabile (possibili problemi di rete)
  - > 2% indica problemi seri (controllare log app)
- **Cause comuni**: Modello non caricato, encoding issue, memoria esaurita

### 3. **Latency (p50/p90)** (`⏱️ API Latency`)
- Queries: `histogram_quantile(0.5|0.9, ...)`
- **Cosa guardare:**
  - **p50** (mediana) = latenza tipica → dovrebbe essere bassa e stabile
  - **p90** (90° percentile) = latenza dei casi lenti → accettabile se < 3x la p50
  - Se p90 cresce mentre p50 resta basso → code di attesa
  - Se entrambi salgono → possibile sobraccarico o slow inference
- **Azioni**:
  - Aumentare CPU/GPU
  - Implementare caching
  - Scalare orizzontalmente

### 4. **Sentiment Distribution** (`💭 Sentiment Distribution`)
- Query: `sum(rate(app_sentiment_predictions_total[5m])) by (sentiment_label)`
- **Cosa guardare**:
  - Proporzione di positive/neutral/negative nel tempo
  - Se il `positive` crolla → possibile crisi reputazionale
  - Se il `negative` sale → sentiment pubblico sta peggiorando
  - Cambio drastico nella distribuzione → possibile shift nei dati
- **Utilità per valutatori**: **Mostra che il sistema sta tracciando il sentiment** come richiesto dalla traccia

### 5. **Model Performance (F1 & Accuracy)** (`🎯 Model Performance`)
- Queries: `model_f1_score{...}`, `model_accuracy{...}`
- **Cosa guardare**:
  - Linee dovrebbero restare stabili o salire (mai scendere significativamente)
  - Se scende → possibile data drift non catturato dai controlli
  - Jumping points = momenti di retraining + promozione
- **Azioni se scende**:
  - Verificare il dataset di training
  - Controllare i report di drift in `artifacts/`
  - Abbassare la soglia di drift per trigger più frequente

### 6. **Data Drift Timeline** (`📉 Data Drift Timeline`)
- Query: `data_drift_flag`
- **Cosa guardare**:
  - Quando il valore salta a 1 → drift rilevato, retraining triggerato
  - Dovrebbe tornare a 0 dopo il retraining (o rimane 1 se il drift persiste)
  - Frequenza dei picchi = frequenza del retraining
- **Interpretazione**:
  - Picchi rari (< 1 volta a settimana) → dati stabili, buon segno
  - Picchi frequenti (> 1 volta al giorno) → dati instabili, possibile problema upstream

---

## 🔍 Come Diagnosticare Problemi

### "L'error rate sta salendo"
```bash
# 1. Controlla i log della app
docker logs machineinnovatorsinc_proai-app-1 | tail -50

# 2. Verifica la disponibilità del modello
curl http://localhost:8000/health

# 3. Prova a fare una predizione manuale
curl -X POST http://localhost:8000/predict \
  -H 'Content-Type: application/json' \
  -d '{"text": "test"}'
```

### "Il sentiment è cambiato drasticamente"
```bash
# 1. Controlla il report di drift
cat artifacts/drift_report.json | jq '.'

# 2. Verifica il flag di drift in Prometheus
curl "http://localhost:9090/api/v1/query?query=data_drift_flag"

# 3. Guarda i log del DAG di drift detection
docker logs machineinnovatorsinc_proai-airflow-1 | grep -i drift
```

### "Il modello F1 è sceso"
```bash
# 1. Controlla quale versione è in Production
curl http://localhost:5000/api/2.0/model-versions | jq '.[] | select(.stage == "Production")'

# 2. Guarda le metriche della versione precedente
curl http://localhost:5000/api/2.0/registered-models/Sentiment | jq '.latest_versions'

# 3. Leggi il report di valutazione
cat artifacts/eval_report.txt  # se esiste
```

---

## ✅ Verifiche Rapide da Terminale

### Query Prometheus via REST API
```bash
# Ultimo valore di F1 score
curl -s "http://localhost:9090/api/v1/query?query=model_f1_score" | jq '.data.result'

# Ultimo valore di drift flag
curl -s "http://localhost:9090/api/v1/query?query=data_drift_flag" | jq '.data.result'

# Request rate (ultime 5 minuti)
curl -s "http://localhost:9090/api/v1/query?query=rate(app_requests_total[5m])" | jq '.data.result'
```

### Sample delle metriche esposte dall'app
```bash
curl http://localhost:8000/metrics | head -30
```

### Verifica che Prometheus sta scrappando
```bash
# Accedi a Prometheus UI
open http://localhost:9090

# Vai su Status → Targets
# Dovresti vedere:
# - app:8000 (UP)
# - pushgateway:9091 (UP)
```

---

## 📝 Note per Valuatori/Sviluppatori

Questa documentazione supporta i **requisiti della traccia d'esame**:
- ✅ **Monitoraggio Continuo della Reputazione**: Sentiment distribution panel + sentiment predictions timeline
- ✅ **Model Performance Tracking**: F1/accuracy panels aggiornati dopo ogni retraining
- ✅ **Data Drift Detection Visualization**: Drift flag timeline + reports in `artifacts/`
- ✅ **System Health Monitoring**: Request rate, error rate, latency (p50/p90)

Tutti i pannelli sono configurati per auto-refresh ogni 10 secondi, permettendo **osservazione in tempo reale** dei modelli e della reputazione online dell'azienda.
