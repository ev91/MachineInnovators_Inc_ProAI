#!/usr/bin/env bash
# Deep cleanup: remove containers, images, volumes, caches
# WARNING: This removes data!
# Usage: ./scripts/clean-all.sh

set -euo pipefail

echo "================================="
echo "  WARNING: AGGRESSIVE CLEANUP"
echo "================================="
echo "[!] This will remove:"
echo "    - All docker compose containers and volumes"
echo "    - MLOps runs history (mlruns/)"
echo "    - Docker system prune (unused images, layers, networks)"
echo ""
read -p "[?] Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "[*] Cancelled"
  exit 0
fi

echo
echo "[*] Stopping stack..."
docker compose down -v || true

echo "[*] Pruning Docker system..."
docker system prune -af --volumes || true

echo "[*] Removing MLOps runs history..."
rm -rf mlruns/* || true
mkdir -p mlruns

echo "[✓] Cleanup complete"
