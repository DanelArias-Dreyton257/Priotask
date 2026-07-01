#!/usr/bin/env bash
# Seeds priotask.db with an admin/admin user and a varied set of demo tasks
# (overdue, due today/this week/this month, different efforts/importances/
# types, a couple already completed, one partially logged) so the UI can be
# exercised without registering and typing tasks by hand.
set -euo pipefail
cd "$(dirname "$0")/.."

python scripts/seed_demo_data.py "${1:-priotask.db}"
