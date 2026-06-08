#!/usr/bin/env bash
# Monthly attendance check — runs daily at 17:30, acts only on last working day
set -euo pipefail

if [ -f "$HOME/.bashrc" ]; then source "$HOME/.bashrc" >/dev/null 2>&1 || true; fi

PYTHON="${PYTHON:-/home/yhr/anaconda3/bin/python3}"
SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ "$SOURCE" != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
echo "[attendance] $(date)"
exec "$PYTHON" "$SCRIPT_DIR/monthly_attendance.py" "$@"
