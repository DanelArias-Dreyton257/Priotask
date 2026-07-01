#!/usr/bin/env bash
# Launches the server and client together, in one terminal, instead of two
# separate `python -m server.src.Server` / `python -m client.src.Client` calls.
set -euo pipefail
cd "$(dirname "$0")/.."

cleanup() {
    echo "Stopping server and client..."
    kill "$SERVER_PID" "$CLIENT_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

python -m server.src.Server &
SERVER_PID=$!

python -m client.src.Client &
CLIENT_PID=$!

wait
