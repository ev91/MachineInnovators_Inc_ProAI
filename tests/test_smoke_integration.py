"""
Smoke Integration Test per docker compose stack

Questo test verifica che:
1. Lo stack docker compose parta correttamente
2. L'endpoint /health della FastAPI app sia raggiungibile e risponda "ok"
3. L'endpoint /predict funzioni con una richiesta di esempio

Come eseguire:
  pytest tests/test_smoke_integration.py -v

Nota: Questo test avvia docker compose e attende che l'app sia ready.
      Prima di eseguirlo, assicurati che le porte (8000, 5000, 8080, 9090, 3000)
      non siano occupate, altrimenti modifica .env
"""

import os
import subprocess
import time
import requests
import pytest


# Configurazione
DOCKER_COMPOSE_FILE = "docker-compose.yml"
APP_URL = os.getenv("APP_URL", "http://localhost:8000")
APP_PORT = os.getenv("APP_PORT", "8000")
MAX_RETRIES = 30  # ~60 secondi con 2 sec per retry
RETRY_DELAY = 2  # secondi


@pytest.fixture(scope="module")
def docker_stack():
    """
    Fixture che avvia il docker compose stack all'inizio del test
    e lo abbatte al termine.
    """
    print("\n[SMOKE TEST] Avvio docker compose stack...")
    
    # Controlla se docker compose è disponibile
    try:
        subprocess.run(["docker", "compose", "version"], check=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        pytest.skip(f"docker compose non disponibile: {e}")
    
    # Controlla se il file compose esiste
    if not os.path.isfile(DOCKER_COMPOSE_FILE):
        pytest.skip(f"{DOCKER_COMPOSE_FILE} non trovato")
    
    # Avvia lo stack
    try:
        result = subprocess.run(
            ["docker", "compose", "up", "--build", "-d"],
            check=True,
            capture_output=True,
            text=True,
        )
        print("[SMOKE TEST] docker compose up completato")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        pytest.fail(f"docker compose up failed: {e.stderr}")
    
    # Attendi che l'app sia pronta
    print(f"[SMOKE TEST] Attendo che l'app sia pronta su {APP_URL}...")
    _wait_for_app_ready(APP_URL)
    
    yield  # Test runs here
    
    # Cleanup: abbatti lo stack
    print("\n[SMOKE TEST] Abbatto docker compose stack...")
    try:
        subprocess.run(
            ["docker", "compose", "down", "--volumes", "--remove-orphans"],
            check=True,
            capture_output=True,
        )
        print("[SMOKE TEST] docker compose down completato")
    except subprocess.CalledProcessError as e:
        print(f"[SMOKE TEST] Errore durante cleanup: {e.stderr}")


def _wait_for_app_ready(app_url, max_retries=MAX_RETRIES, retry_delay=RETRY_DELAY):
    """
    Attendi che l'app sia pronta controllando l'endpoint /health
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{app_url}/health", timeout=5)
            if response.status_code == 200:
                print(f"[SMOKE TEST] App is ready (attempt {attempt + 1})")
                return
        except (requests.ConnectionError, requests.Timeout):
            pass
        
        if attempt < max_retries - 1:
            print(f"[SMOKE TEST] Tentativo {attempt + 1}/{max_retries}, retry tra {retry_delay}s...")
            time.sleep(retry_delay)
    
    pytest.fail(f"App non è diventata ready dopo {max_retries} tentativi ({max_retries * retry_delay}s)")


def test_health_endpoint(docker_stack):
    """
    Test: l'endpoint /health ritorna {"status": "ok"}
    """
    response = requests.get(f"{APP_URL}/health", timeout=10)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert "status" in data, "Response deve contenere 'status'"
    assert data["status"] == "ok", f"Expected status='ok', got {data['status']}"


def test_predict_endpoint(docker_stack):
    """
    Test: l'endpoint /predict accetta una richiesta e ritorna un risultato valido
    """
    payload = {"text": "I love this product!"}
    response = requests.post(
        f"{APP_URL}/predict",
        json=payload,
        timeout=10,
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    
    # Verifica che la risposta contenga i campi attesi
    assert "label" in data, "Response deve contenere 'label'"
    assert data["label"] in {"positive", "neutral", "negative"}, \
        f"Label deve essere uno tra positive/neutral/negative, got {data['label']}"
    
    # Verifica che il score sia presente e valido
    if "score" in data:
        assert 0.0 <= data["score"] <= 1.0, f"Score deve essere tra 0 e 1, got {data['score']}"


def test_predict_edge_cases(docker_stack):
    """
    Test: /predict funziona con testi diversi
    """
    test_cases = [
        {"text": "Great product!", "expected_label": "positive"},
        {"text": "Not bad", "expected_label": None},  # Non predeterminiamo il label esatto
        {"text": "I hate this", "expected_label": "negative"},
        {"text": "ok", "expected_label": None},
    ]
    
    for test_case in test_cases:
        response = requests.post(
            f"{APP_URL}/predict",
            json={"text": test_case["text"]},
            timeout=10,
        )
        assert response.status_code == 200, \
            f"Failed for text '{test_case['text']}': {response.text}"
        
        data = response.json()
        assert "label" in data, f"Missing 'label' for text '{test_case['text']}'"
        assert data["label"] in {"positive", "neutral", "negative"}


def test_metrics_endpoint(docker_stack):
    """
    Test: l'endpoint /metrics espone metriche Prometheus
    """
    response = requests.get(f"{APP_URL}/metrics", timeout=10)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    # Verifica che siano presenti le metriche principali
    metrics_text = response.text
    expected_metrics = [
        "app_requests_total",
        "app_errors_total",
        "app_request_latency_seconds",
        "data_drift_flag",
    ]
    
    for metric in expected_metrics:
        assert metric in metrics_text, f"Metrica '{metric}' non trovata in /metrics"
