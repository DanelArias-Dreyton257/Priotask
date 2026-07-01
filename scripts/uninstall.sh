#!/usr/bin/env bash
# Removes the Priotask installation from this machine:
#   1. Deletes the 'priotask' conda environment.
#   2. Optionally deletes the database file (prompts unless FORCE=1).
#
# The repo directory itself is NOT removed — do that manually if wanted.
#
# Usage:
#   ./scripts/uninstall.sh            # interactive
#   FORCE=1 ./scripts/uninstall.sh   # no prompts
set -euo pipefail
cd "$(dirname "$0")/.."

DB_PATH="${1:-priotask.db}"

# --- database ---
if [[ -f "$DB_PATH" ]]; then
    if [[ "${FORCE:-}" == "1" ]]; then
        rm -f "$DB_PATH"
        echo "Removed $DB_PATH."
    else
        read -r -p "Delete database '$DB_PATH' (all users and tasks)? [y/N] " confirm
        if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
            rm -f "$DB_PATH"
            echo "Removed $DB_PATH."
        else
            echo "Database kept."
        fi
    fi
fi

# --- conda environment ---
if conda env list | grep -q '^priotask '; then
    echo "==> Removing conda environment 'priotask'..."
    conda env remove -n priotask -y
    echo "    Done."
else
    echo "Conda environment 'priotask' not found, nothing to remove."
fi

echo "Uninstall complete."
