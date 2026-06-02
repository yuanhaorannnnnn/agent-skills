#!/usr/bin/env bash
# Friday 18:00 — generate weekly checklist and send to DingTalk
set -euo pipefail

if [ -f "$HOME/.bashrc" ]; then source "$HOME/.bashrc" 2>/dev/null || true; fi
if [ -f "$HOME/.profile" ]; then source "$HOME/.profile" 2>/dev/null || true; fi

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    if [ -f "$HOME/.anthropic_api_key" ]; then
        export ANTHROPIC_API_KEY=$(cat "$HOME/.anthropic_api_key" | tr -d '\\n')
    fi
fi

PYTHON="${PYTHON:-/home/yhr/anaconda3/bin/python3}"
if [ -z "${ANTHROPIC_BASE_URL:-}" ]; then
    export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
fi
if [ -z "${ANTHROPIC_MODEL:-}" ]; then
    export ANTHROPIC_MODEL="deepseek-v4-pro[1m]"
fi

# OASIS SIM 产品开发群成员
export REPORT_RECEIVERS="1629077236740667,12365829611219204,16677841294378345,16630305268849065,17113372241822640,16454069611218832,1642554671495110,16935374573524248,17119352041538685,1753665012576918,16092186407543021,16455842823636252"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "[friday-review] $(date)"
exec "$PYTHON" "$SCRIPT_DIR/friday_review.py" "$@"
