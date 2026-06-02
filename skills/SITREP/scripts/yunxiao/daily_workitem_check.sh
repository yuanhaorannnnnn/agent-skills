#!/usr/bin/env bash
# Daily 10:00 cloud efficiency work item check
set -euo pipefail
PYTHON="${PYTHON:-/home/yhr/anaconda3/bin/python3}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "[yunxiao-check] $(date)"
exec "$PYTHON" "$SCRIPT_DIR/daily_workitem_check.py"
