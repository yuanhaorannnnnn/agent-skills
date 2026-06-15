#!/usr/bin/env bash
# Sunday 23:00 — read back checklist, apply overrides, submit report
set -euo pipefail

if [ -f "$HOME/.bashrc" ]; then source "$HOME/.bashrc" >/dev/null 2>&1 || true; fi
if [ -f "$HOME/.profile" ]; then source "$HOME/.profile" >/dev/null 2>&1 || true; fi

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    if [ -f "$HOME/.anthropic_api_key" ]; then
        export ANTHROPIC_API_KEY=$(cat "$HOME/.anthropic_api_key" | tr -d '\\n')
    fi
fi

# Cron may run after the short-lived DingTalk access token expires. Refresh it
# from the stored refresh token before reading checklist docs or submitting.
if command -v dws >/dev/null 2>&1; then
    dws auth status --format json >/dev/null 2>&1 || true
fi

PYTHON="${PYTHON:-/home/yhr/anaconda3/bin/python3}"
if [ -z "${ANTHROPIC_BASE_URL:-}" ]; then
    export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
fi
if [ -z "${ANTHROPIC_MODEL:-}" ]; then
    export ANTHROPIC_MODEL="deepseek-v4-pro[1m]"
fi


SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ "$SOURCE" != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
echo "[sunday-finalize] $(date)"
exec "$PYTHON" "$SCRIPT_DIR/sunday_finalize.py" "$@"
