#!/usr/bin/env bash
# Sets up Priotask from scratch on a machine that already has conda:
#   1. Creates the 'priotask' conda environment from environment.yml.
#   2. Downloads the Playwright Chromium browser (used by the JS test suite).
#   3. Initialises an empty priotask.db so the server is ready to start.
#
# Run once after cloning the repo:
#   ./scripts/install.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Creating conda environment 'priotask' from environment.yml..."
if conda env list | grep -q '^priotask '; then
    echo "    Environment already exists — updating instead."
    conda env update -f environment.yml --prune
else
    conda env create -f environment.yml
fi

echo "==> Downloading Playwright Chromium browser..."
conda run -n priotask python -m playwright install chromium

echo "==> Initialising database (first server start creates priotask.db)..."
# Start the server briefly so it runs CREATE TABLE IF NOT EXISTS, then stop it.
conda run -n priotask python -m server.src.Server &
SERVER_PID=$!
sleep 3
kill "$SERVER_PID" 2>/dev/null || true
wait "$SERVER_PID" 2>/dev/null || true

echo ""
echo "Priotask is ready."
echo "  Run the app:       ./scripts/run.sh"
echo "  Seed demo data:    conda run -n priotask python scripts/seed_demo_data.py"
echo "  Run tests:         conda run -n priotask python -m unittest discover -s server/test -p '*_test.py'"
echo "                     conda run -n priotask python -m unittest discover -s client/test -p '*_test.py'"
