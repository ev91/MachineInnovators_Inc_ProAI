"""
Push model performance metrics (F1, accuracy) from MLflow to Prometheus Pushgateway.

Usage:
    python -m src.monitoring.push_model_metrics \
        --model_uri models:/Sentiment/Production \
        --metrics_json /path/to/metrics.json \
        --gateway http://pushgateway:9091
"""

import argparse
import logging
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

logger = logging.getLogger(__name__)


def push_metrics(
    gateway: str,
    job: str,
    instance: str,
    model_name: str,
    model_version: str,
    f1_score: float,
    accuracy: float,
):
    """
    Push model performance metrics to Pushgateway.

    Args:
        gateway: Pushgateway URL (e.g., "http://pushgateway:9091")
        job: Job name (e.g., "model_performance")
        instance: Instance label (e.g., "airflow")
        model_name: Model name (e.g., "Sentiment")
        model_version: Model version number (e.g., "3")
        f1_score: F1 macro score (0.0-1.0)
        accuracy: Accuracy score (0.0-1.0)
    """
    reg = CollectorRegistry()

    # Create gauges for model metrics
    f1_gauge = Gauge(
        "model_f1_score",
        "Model macro F1 score",
        ["model_name", "model_version"],
        registry=reg,
    )
    acc_gauge = Gauge(
        "model_accuracy",
        "Model accuracy",
        ["model_name", "model_version"],
        registry=reg,
    )

    # Set values
    f1_gauge.labels(model_name=model_name, model_version=model_version).set(f1_score)
    acc_gauge.labels(model_name=model_name, model_version=model_version).set(
        accuracy
    )

    # Push to gateway
    push_to_gateway(
        gateway,
        job=job,
        grouping_key={"instance": instance},
        registry=reg,
    )

    logger.info(
        f"[push_model_metrics] Pushed to {gateway}: F1={f1_score:.4f}, Accuracy={accuracy:.4f}"
    )


def main():
    ap = argparse.ArgumentParser(
        description="Push model performance metrics to Prometheus"
    )
    ap.add_argument(
        "--gateway",
        default="http://pushgateway:9091",
        help="Pushgateway URL",
    )
    ap.add_argument(
        "--job",
        default="model_performance",
        help="Job name",
    )
    ap.add_argument(
        "--instance",
        default="airflow",
        help="Instance label",
    )
    ap.add_argument(
        "--model_name",
        default="Sentiment",
        help="Model name",
    )
    ap.add_argument(
        "--model_version",
        type=str,
        required=True,
        help="Model version",
    )
    ap.add_argument(
        "--f1_score",
        type=float,
        required=True,
        help="F1 macro score (0.0-1.0)",
    )
    ap.add_argument(
        "--accuracy",
        type=float,
        required=True,
        help="Accuracy score (0.0-1.0)",
    )

    args = ap.parse_args()

    push_metrics(
        gateway=args.gateway,
        job=args.job,
        instance=args.instance,
        model_name=args.model_name,
        model_version=args.model_version,
        f1_score=args.f1_score,
        accuracy=args.accuracy,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
