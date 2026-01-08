from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel
import time

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

from src.serving.load_model import predict_fn


# ====================================================
# 1) PRIMA si crea l'app
# ====================================================
app = FastAPI()

# ====================================================
# 2) Poi si definiscono le metriche
# ====================================================
REQUEST_COUNT = Counter("app_requests_total", "Total prediction requests")

ERROR_COUNT = Counter("app_errors_total", "Total prediction errors")

REQUEST_LATENCY = Histogram("app_request_latency_seconds", "Prediction latency")

SENTIMENT_PREDICTIONS = Counter(
    "app_sentiment_predictions_total",
    "Total sentiment predictions by label",
    ["sentiment_label"],
)

DRIFT_FLAG = Gauge("data_drift_flag", "1 if drift detected else 0")


# ====================================================
# 3) Solo ORA: startup event
# ====================================================
@app.on_event("startup")
def startup_event():
    DRIFT_FLAG.set(0)


# ====================================================
# API
# ====================================================
class Item(BaseModel):
    text: str


@app.post("/predict")
def predict(item: Item):
    start = time.time()
    try:
        label, score = predict_fn(item.text)
        REQUEST_COUNT.inc()
        SENTIMENT_PREDICTIONS.labels(sentiment_label=label).inc()
        return {"label": label, "score": score}
    except Exception as e:
        ERROR_COUNT.inc()
        return {"error": str(e)}
    finally:
        REQUEST_LATENCY.observe(time.time() - start)


@app.get("/")
def root():
    return {"message": "working!"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
