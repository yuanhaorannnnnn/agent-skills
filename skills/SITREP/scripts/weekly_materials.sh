#!/usr/bin/env bash
# Friday 17:30 — generate weekly report reference materials DingTalk doc.
set -euo pipefail

if [ -f "$HOME/.bashrc" ]; then source "$HOME/.bashrc" >/dev/null 2>&1 || true; fi
if [ -f "$HOME/.profile" ]; then source "$HOME/.profile" >/dev/null 2>&1 || true; fi

PYTHON="${PYTHON:-/home/yhr/anaconda3/bin/python3}"

# Cron may run after the short-lived DingTalk access token expires. Refresh it
# from the stored refresh token before creating docs or sending messages.
if command -v dws >/dev/null 2>&1; then
    dws auth status --format json >/dev/null 2>&1 || true
fi

SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ "$SOURCE" != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"

echo "[weekly-materials] $(date)"
exec "$PYTHON" "$SCRIPT_DIR/weekly_materials.py" "$@"
