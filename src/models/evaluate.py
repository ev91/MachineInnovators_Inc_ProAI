import argparse
import json
import mlflow
import mlflow.pyfunc
import pandas as pd
from sklearn.metrics import f1_score, accuracy_score
from src.utils.mlflow_utils import (
    get_production_model_uri,
    promote_to_stage,
    REGISTERED_NAME,
)

_LABEL_MAP = {"LABEL_0": "negative", "LABEL_1": "neutral", "LABEL_2": "positive"}


def _normalize(label: str) -> str:
    if label.startswith("LABEL_"):
        return _LABEL_MAP.get(label, label)
    return label.lower()


def _predict_df(model, df: pd.DataFrame) -> list[str]:
    preds = []
    for text in df["text"].tolist():
        out = model.predict([text])[0]
        # out può essere una stringa (sklearn) o un dict con "label" (transformers)
        if isinstance(out, dict):
            preds.append(_normalize(out["label"]))
        else:
            preds.append(_normalize(out))
    return preds


def evaluate_and_maybe_promote(
    new_model_uri: str, eval_csv: str, min_improvement: float = 0.0
) -> dict:
    """
    Evaluate new model vs production and promote if better.

    Returns:
        dict with evaluation metrics: {
            "new_f1": float,
            "new_accuracy": float,
            "new_version": int,
            "promoted": bool
        }
    """
    df = pd.read_csv(eval_csv)
    y_true = df["label"].astype(str).str.lower().tolist()

    # Valuta nuovo modello
    new_model = mlflow.pyfunc.load_model(new_model_uri)
    new_pred = _predict_df(new_model, df)
    new_f1 = f1_score(y_true, new_pred, average="macro")
    new_accuracy = accuracy_score(y_true, new_pred)

    # Valuta production corrente (se esiste)
    prod_uri = get_production_model_uri(REGISTERED_NAME)
    if prod_uri:
        prod_model = mlflow.pyfunc.load_model(prod_uri)
        prod_pred = _predict_df(prod_model, df)
        prod_f1 = f1_score(y_true, prod_pred, average="macro")
    else:
        prod_f1 = -1.0  # forza promozione alla prima

    print({"new_f1": new_f1, "new_accuracy": new_accuracy, "prod_f1": prod_f1})

    promoted = False
    version = None

    if new_f1 >= prod_f1 + min_improvement:
        # Estrai version da new_model_uri: runs:/.../model oppure models:/...
        client = mlflow.tracking.MlflowClient()
        # Recupera l'ultima versione registrata (quella appena loggata)
        versions = client.get_latest_versions(REGISTERED_NAME, stages=["None"]) or []
        if not versions:
            # fallback: prendi la più recente tra tutte
            allv = client.search_model_versions(f"name='{REGISTERED_NAME}'")
            versions = sorted(allv, key=lambda v: int(v.version), reverse=True)
        version = int(versions[0].version)
        promote_to_stage(REGISTERED_NAME, version, stage="Production")
        promoted = True
        print(f"Promosso {REGISTERED_NAME} v{version} → Production")
    else:
        print("Nessuna promozione: nuovo modello non migliora.")
        # Comunque ritorna la versione per il log delle metriche
        client = mlflow.tracking.MlflowClient()
        versions = client.get_latest_versions(REGISTERED_NAME, stages=["None"]) or []
        if not versions:
            allv = client.search_model_versions(f"name='{REGISTERED_NAME}'")
            versions = sorted(allv, key=lambda v: int(v.version), reverse=True)
        if versions:
            version = int(versions[0].version)

    return {
        "new_f1": round(new_f1, 4),
        "new_accuracy": round(new_accuracy, 4),
        "new_version": version,
        "promoted": promoted,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--new_model_uri",
        required=True,
        help="es. runs:/<run_id>/model oppure models:/Sentiment/None",
    )
    ap.add_argument("--eval_csv", required=True, help="CSV con colonne: text,label")
    ap.add_argument("--min_improvement", type=float, default=0.0)
    ap.add_argument(
        "--metrics_output",
        default=None,
        help="Path file JSON per salvare le metriche (opzionale)",
    )
    args = ap.parse_args()

    metrics = evaluate_and_maybe_promote(
        args.new_model_uri, args.eval_csv, args.min_improvement
    )

    # Stampa le metriche in JSON per cattura dal DAG
    print(f"METRICS_JSON: {json.dumps(metrics)}")

    # Salva su file se richiesto
    if args.metrics_output:
        with open(args.metrics_output, "w") as f:
            json.dump(metrics, f, indent=2)
        print(f"Metriche salvate in {args.metrics_output}")
