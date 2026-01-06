# MLOps Sentiment Analysis – Utility Scripts

Questo folder contiene gli script utility standard per il management dello stack docker compose.

## Comandi disponibili

### `./up.sh [--build]`
Avvia lo stack docker compose completo.
```bash
./scripts/up.sh              # Avvia (immagini già buildete)
./scripts/up.sh --build      # Build e avvia
```

### `./down.sh`
Ferma e rimuove il stack (volumi inclusi).
```bash
./scripts/down.sh
```

### `./logs.sh [service]`
Visualizza i log da uno o più servizi.
```bash
./scripts/logs.sh            # Tutti i servizi
./scripts/logs.sh app        # Solo FastAPI
./scripts/logs.sh airflow    # Solo Airflow
./scripts/logs.sh mlflow     # Solo MLflow
```

### `./clean-all.sh`
Cleanup aggressivo: rimuove containers, volumi, mlruns, prune docker.
```bash
./scripts/clean-all.sh  # Chiede conferma prima di cancellare
```

## Note

- Tutti gli script assumono di essere eseguiti dalla root del repository
- I nomi sono standard e coerenti (a differenza dei vecchi script caotici)
- Usano `docker compose` (v2, non `docker-compose`)
- Supportano variabili d'ambiente da `.env`

## Script vecchi (deprecati)

Gli script originali (`clean_all.sh`, `init_containers.sh`, `launch_stuff.sh`, `pulizia.SH`, `reset_and_run_conteiners.sh`) rimangono nel root per backward compatibility, ma si consiglia di usare i nuovi script in questa cartella.

Leggi il [README.md](../README.md) per il quickstart.
