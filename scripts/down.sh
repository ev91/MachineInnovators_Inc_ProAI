#!/usr/bin/env bash
# Stop and remove the docker compose stack
# Usage: ./scripts/down.sh

set -euo pipefail

echo "================================="
echo "  MachineInnovators – Stack DOWN"
echo "================================="
echo

echo "[*] Stopping docker compose stack..."
docker compose down -v || true

echo "[✓] Stack stopped and cleaned"
