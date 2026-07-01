#!/usr/bin/env bash
# Updates an existing Priotask installation after pulling new code:
#   1. Updates the 'priotask' conda environment from environment.yml
#      (adds new packages, removes ones no longer listed, won't downgrade Python).
#   2. Re-runs 'playwright install chromium' in case the pinned version changed.
#   3. Runs any pending DB migrations (the server's connect() runs ALTER TABLE
#      for missing columns on every startup, so a brief start is enough).
#
# If environment.yml changed Python's version constraint and your existing env
# predates that change, recreate it instead:
#   conda env remove -n priotask && conda env create -f environment.yml
#
# Usage (from the repo root or anywhere):
#   ./scripts/update.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Updating conda environment 'priotask'..."
conda env update -f environment.yml --prune

echo "==> Updating Playwright Chromium browser..."
conda run -n priotask python -m playwright install chromium

echo "==> Applying any pending DB migrations..."
conda run -n priotask python -m server.src.Server &
SERVER_PID=$!
sleep 3
kill "$SERVER_PID" 2>/dev/null || true
wait "$SERVER_PID" 2>/dev/null || true

echo ""
echo "Update complete. Restart the app to pick up the changes: ./scripts/run.sh"
