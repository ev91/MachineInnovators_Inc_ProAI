#!/usr/bin/env bash
# View logs from the docker compose stack
# Usage: ./scripts/logs.sh [service-name]

set -euo pipefail

SERVICE="${1:-}"

echo "================================="
echo "  MachineInnovators – Logs"
echo "================================="
echo

if [[ -z "$SERVICE" ]]; then
  echo "[*] Showing logs from all services (Ctrl+C to stop)..."
  docker compose logs -f
else
  echo "[*] Showing logs from service: $SERVICE (Ctrl+C to stop)..."
  docker compose logs -f "$SERVICE"
fi
