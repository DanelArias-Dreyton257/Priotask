#!/usr/bin/env bash
# Wipes priotask.db (all users, tasks and trained PrioritizerNetwork weights)
# so the next server start creates a fresh, empty database.
set -euo pipefail
cd "$(dirname "$0")/.."

DB_PATH="${1:-priotask.db}"

if [[ ! -f "$DB_PATH" ]]; then
    echo "$DB_PATH does not exist, nothing to do."
    exit 0
fi

if [[ "${FORCE:-}" != "1" ]]; then
    read -r -p "This will permanently delete $DB_PATH and all its data. Continue? [y/N] " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        echo "Aborted."
        exit 1
    fi
fi

rm -f "$DB_PATH"
echo "$DB_PATH removed."
