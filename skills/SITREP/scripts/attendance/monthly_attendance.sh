#!/usr/bin/env bash
# Monthly attendance check — runs daily at 17:30, acts only on last working day
set -euo pipefail

if [ -f "$HOME/.bashrc" ]; then source "$HOME/.bashrc" 2>/dev/null || true; fi

PYTHON="${PYTHON:-/home/yhr/anaconda3/bin/python3}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "[attendance] $(date)"
exec "$PYTHON" "$SCRIPT_DIR/monthly_attendance.py"
