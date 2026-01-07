# MLOps Sentiment Analysis – Online Reputation Monitoring

**Machine Innovators Inc.** – Piattaforma di monitoraggio del sentiment online con ritraining automatico, MLflow registry e dashboard di monitoring in tempo reale.

> **Modello**: [cardiffnlp/twitter-roberta-base-sentiment-latest](https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest) (RoBERTa fine-tuned per sentiment su Twitter)
>
> **Nota sulla traccia**: La traccia dell'esame menziona FastText, ma il modello indicato nel link è RoBERTa. Il progetto utilizza il modello HuggingFace linkato per migliore accuracy su testi brevi e social media.

---

## 🚀 Quick Start (5 minuti)

### Requisiti
- **Docker** e **Docker Compose** (v2.0+)
- **Python 3.10+** (opzionale, solo per esecuzione locale senza container)

### Avvia lo stack completo
```bash
# Clone e avvia
git clone https://github.com/ev91/MachineInnovators_Inc_ProAI.git
cd MachineInnovators_Inc_ProAI

# Prepara variabili d'ambiente (opzionale, usa i default)
# cp .env.example .env

# Avvia il stack
docker compose up --build
```

**Attendi ~60–90 secondi** finché tutti i servizi sono `running`:
```
✓ app (FastAPI)              → http://localhost:8000
✓ mlflow (Model Registry)    → http://localhost:5000
✓ airflow (Orchestration)    → http://localhost:8080
✓ prometheus (Metrics DB)    → http://localhost:9090
✓ grafana (Dashboards)       → http://localhost:3000
```

### Test rapido dell'API
```bash
# Health check
curl http://localhost:8000/health

# Predizione di sentiment
curl -X POST http://localhost:8000/predict \
  -H 'Content-Type: application/json' \
  -d '{"text": "I love this product!"}'
```

---

## 📖 Documentazione

### Per sviluppatori/valuatori
1. **[Panoramica della codebase](docs/codebase_overview.md)** – Architettura, componenti, flusso dati
2. **[Metriche e Monitoring](docs/metrics_guide.md)** – Come leggere Prometheus/Grafana
3. **[Training e Promozione Modello](docs/training_and_promotion.md)** – Flusso MLflow, retraining
4. **[Simulazione Data Drift](docs/data_drift_simulation.md)** – Come testare il rilevamento drift
5. **[Delivery Status](docs/DELIVERY_STATUS.md)** – Checklist consegna, componenti implementati, stato progetto

### Per la consegna (Google Colab)
👉 **[Notebook di consegna](notebooks/Deliverable_Colab.ipynb)** – Demo di inferenza, link al repo, istruzioni per lo stack completo.

---

## ⚙️ Configurazione

### Variabili d'ambiente

Tutte le porte e i percorsi dei modelli sono configurabili. Crea un file `.env` dal template:

```bash
cp .env.example .env
```

Variabili principali:

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `APP_PORT` | 8000 | Porta FastAPI |
| `MLFLOW_PORT` | 5000 | Porta MLflow UI |
| `AIRFLOW_PORT` | 8080 | Porta Airflow UI |
| `PROM_PORT` | 9090 | Porta Prometheus |
| `PUSHGATEWAY_PORT` | 9091 | Porta Pushgateway |
| `GRAFANA_PORT` | 3000 | Porta Grafana |
| `MODEL_URI` | _(vuoto)_ | URI MLflow (es. `models:/Sentiment/Production`) per servire il modello in Produzione |
| `REGISTERED_MODEL_NAME` | `Sentiment` | Nome del modello nel registry MLflow |

Per dettagli completi vedi [.env.example](.env.example).

---

## 📊 Componenti dello stack

### FastAPI (Serving)
Espone tre endpoint principali:
- **`GET /health`** – Health check (ritorna `{"status": "ok"}`)
- **`POST /predict`** – Classifica sentiment (input: `{"text": "..."}`, output: `{"label": "positive|neutral|negative", "score": 0.0-1.0}`)
- **`GET /metrics`** – Metriche Prometheus in formato standard

Carica il modello dal registry MLflow (se `MODEL_URI` è impostato) oppure fallback automatico su HuggingFace.

### MLflow (Model Registry)
Gestisce le versioni del modello, stage (Production/Staging) e artefatti.
- **UI**: http://localhost:5000
- Credenziali: opzionali (default: nessuna autenticazione)

### Airflow (Orchestration)
DAG `retrain_sentiment` che automatizza il pipeline:
1. **ingest** – Carica nuovi batch dati da `data/incoming/`
2. **drift** – Rileva data drift confrontando distribuzioni
3. **branch** – Decide se ritrainare (in base a drift, timer 7gg, o flag `force_retrain`)
4. **train & evaluate** – Addestra e valuta il nuovo modello
5. **promote** – Promuove a Production se migliore della versione corrente
- **UI**: http://localhost:8080
- Credenziali: `admin` / `admin`

### Prometheus + Grafana (Monitoring)
- **Prometheus**: http://localhost:9090 – database time-series
- **Grafana**: http://localhost:3000 – dashboards
  - Credenziali: `admin` / `admin`
  - Dashboard preconfigurata: `MLOps – Sentiment Analysis Monitoring`

Metriche raccolte:
- **API Traffic**: `app_requests_total`, `app_errors_total`, `app_request_latency_seconds`
- **Sentiment Analysis**: `app_sentiment_predictions_total` (per label: positive/neutral/negative) – traccia il sentiment della community nel tempo
- **Model Performance**: `model_f1_score`, `model_accuracy` – metriche aggiornate dopo ogni retraining
- **Data Drift**: `data_drift_flag` – gauge (0=no drift, 1=drift rilevato) che trigga il retraining automatico

Per dettagli su come leggere i pannelli, vedi [docs/metrics_guide.md](docs/metrics_guide.md).

---

## ✅ Uso comune

### Stack quickstart
```bash
# Opzione 1: Script
./scripts/up.sh --build

# Opzione 2: Docker compose diretto
docker compose up --build
```

### Ferma stack
```bash
# Opzione 1: Script
./scripts/down.sh

# Opzione 2: Docker compose diretto
docker compose down -v
```

### Visualizza log
```bash
./scripts/logs.sh              # Tutti i servizi
./scripts/logs.sh app          # Solo app
./scripts/logs.sh airflow      # Solo airflow
```

### Cleanup aggressivo
```bash
./scripts/clean-all.sh  # Rimuove tutto (WARNING: dati perduti)
```

Se preferisci sviluppare localmente:

```bash
# Setup ambiente
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Esegui app
uvicorn src.serving.app:app --reload --port 8000

# O per il training
python -m src.models.train_roberta --experiment sentiment

# O per i test
pytest -v
```

### Test completo
```bash
pytest -v --tb=short
```

### Avvio manuale del DAG (dentro stack)
```bash
docker compose exec airflow airflow dags test retrain_sentiment 2025-01-01
```

### Forzare il ritraining
Dalla UI Airflow, quando triggeri il DAG, passa nel JSON:
```json
{"force_retrain": true}
```

Oppure imposta la Variable `force_retrain=true` in Admin → Variables.

### Demo drift (innesca ritraining automatico)
Il batch di drift è già pronto in `data/incoming/drift_example.csv`:
```bash
docker compose exec app ls data/incoming/drift_example.csv
```

Vedi [docs/data_drift_simulation.md](docs/data_drift_simulation.md) per dettagli.

### Dev/Smoke mode (training rapido per test)
```json
{"dev_smoke": true}
```

Addestra un piccolo modello sklearn in pochi secondi (non promuove a Production). Vedi README Airflow per dettagli.

---

## 🐛 Risoluzione problemi

### Stack non avvia
```bash
# Controlla i log
docker compose logs -f

# Verifica le porte
lsof -i :8000  # app
lsof -i :5000  # mlflow
lsof -i :8080  # airflow

# Se occupate: cambia in .env o uccidi il processo
```

### Airflow webserver "Bad Gateway"
Stale PID file da riavvio anomalo:
```bash
docker compose exec airflow rm -f /opt/airflow/airflow-webserver.pid
docker compose restart airflow
```

### Modello non carica in FastAPI
```bash
docker compose logs app | tail -50
```

Se `MODEL_URI` è impostato ma non esiste in MLflow, fallback automatico su HuggingFace.

### Prima esecuzione lenta
- **Prima inferenza**: ~5–10 sec (download + warm-up modello HF)
- **Successive**: <1 sec (cache in memoria)

### Porte occupate
Se le porte di default sono occupate, modifica in `.env`:
```bash
APP_PORT=9000
MLFLOW_PORT=6000
# ... etc
```

Poi ricrea: `docker compose down && docker compose up --build`

---

## 🎯 Per la valutazione

### Checklist di valutazione
1. ✅ **CI passante**: [.github/workflows/ci.yml](.github/workflows/ci.yml) – lint, test pytest e smoke test docker compose
2. ✅ **Stack reproducibile**: `docker compose up --build` parte pulito e tutti i servizi raggiungibili
3. ✅ **Smoke test**: Test di integrazione che verifica `/health` e `/predict` con il container vero
4. ✅ **Notebook Colab**: [Deliverable_Colab.ipynb](notebooks/Deliverable_Colab.ipynb) con link repo + demo inferenza
5. ✅ **Monitoring**: Prometheus + Grafana con metriche e drift flag in real-time
6. ✅ **Retraining**: DAG Airflow con logica di branch drift-driven e promotion automatica
7. ✅ **Documentazione**: Architettura, setup, troubleshooting, flusso training ben spiegati

### Screenshot e verifiche rapide

**MLflow Registry**:
- Vai su http://localhost:5000 → Models → Sentiment
- Osserva versioni e stage (Production/Staging/None)

**Grafana Dashboard**:
- http://localhost:3000 → Dashboard "MLOps – Sentiment App"
- Osserva request volume, latency (p50/p90), drift flag
- Manda una richiesta a `/predict` → vedi le metriche aggiornarsi in real-time

**Airflow DAG**:
- http://localhost:8080 → DAG `retrain_sentiment`
- Trigger manuale (tasto play) → osserva gli output nei log
- Vedi MLflow e Prometheus aggiornati

**Prometheus Queries**:
```bash
curl "http://localhost:9090/api/v1/query?query=data_drift_flag"
curl "http://localhost:9090/api/v1/query?query=app_requests_total"
```

## 📸 Evidenze (screenshots)

Di seguito sono riportate alcune schermate esemplificative presenti in `docs/screenshots/` utili all'evaluazione:

- ![Airflow DAG](docs/screenshots/Schermata%20Airflow.png) — Airflow: vista del DAG `retrain_sentiment` dopo un run, utile per verificare che i task (ingest/drift/train/evaluate) siano stati eseguiti correttamente.
- ![Grafana Dashboard](docs/screenshots/Schermata%20Grafana.png) — Grafana: dashboard "MLOps – Sentiment App" con pannelli su request volume, latenza (p50/p90) e `data_drift_flag`.
- ![MLflow Registry](docs/screenshots/Schermata%20MLFlow.png) — MLflow: Model Registry che mostra le versioni del modello `Sentiment` e gli stage (Production/Staging/None).
- ![GitHub Actions CI](docs/screenshots/Schermata%20Github%20Actions.png) — GitHub Actions: esempio di run CI (lint, unit tests, smoke test) come prova della pipeline su push/PR.

---

## 🔧 Comandi utili

### Cleanup completo
```bash
docker compose down --volumes --remove-orphans
docker system prune -f
```

### Visualizza i log di un servizio
```bash
docker compose logs -f app
docker compose logs -f airflow
docker compose logs -f mlflow
```

### Esecuzione delle singole task Airflow
```bash
# Ingest dati
docker compose exec airflow airflow tasks test retrain_sentiment ingest 2025-01-01

# Drift detection
docker compose exec airflow airflow tasks test retrain_sentiment drift 2025-01-01

# Training
docker compose exec airflow airflow tasks test retrain_sentiment train 2025-01-01
```

---

## 📝 Note sul timing

> Lo stack richiede **~60–90 secondi** per partire completamente (Airflow + MLflow + Grafana).
> La prima inferenza può impiegare **5–10 secondi** per il download e warm-up del modello HuggingFace;
> le successive sono **<1 secondo** perché la pipeline resta in memoria.

---

## 📜 Licenza e contributi

Progetto sviluppato per **Machine Innovators Inc.** come esercitazione MLOps.

Per domande o contributi, apri una issue su GitHub.
