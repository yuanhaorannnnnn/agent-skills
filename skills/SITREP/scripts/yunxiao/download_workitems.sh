#!/usr/bin/env bash
# Daily 9:00 download assigned work items
set -euo pipefail
PYTHON="${PYTHON:-/home/yhr/anaconda3/bin/python3}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "[yunxiao-download] $(date)"
exec "$PYTHON" "$SCRIPT_DIR/download_workitems.py"
