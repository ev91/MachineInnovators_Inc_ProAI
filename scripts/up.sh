#!/usr/bin/env bash
# Start the complete docker compose stack
# Usage: ./scripts/up.sh [--build]

set -euo pipefail

BUILD=""
if [[ "${1:-}" == "--build" ]]; then
  BUILD="--build"
fi

echo "================================="
echo "  MachineInnovators – Stack UP"
echo "================================="
echo

# Clean up old containers
echo "[*] Cleaning up old containers..."
docker compose down -v || true

# Start the stack
echo "[*] Starting docker compose stack..."
docker compose up $BUILD

echo "[✓] Stack started"
