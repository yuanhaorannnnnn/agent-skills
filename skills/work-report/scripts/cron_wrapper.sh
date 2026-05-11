#!/usr/bin/env bash
# Cron wrapper for work-report weekly generation.
# Ensures environment is properly set before running the report generator.

set -euo pipefail

# Load user environment (for ANTHROPIC_API_KEY and PATH)
if [ -f "$HOME/.bashrc" ]; then
    source "$HOME/.bashrc" 2>/dev/null || true
fi
if [ -f "$HOME/.profile" ]; then
    source "$HOME/.profile" 2>/dev/null || true
fi
if [ -f "$HOME/.zshrc" ]; then
    source "$HOME/.zshrc" 2>/dev/null || true
fi

# Ensure ANTHROPIC_API_KEY is available
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    # Try to load from common secret locations
    if [ -f "$HOME/.anthropic_api_key" ]; then
        export ANTHROPIC_API_KEY=$(cat "$HOME/.anthropic_api_key" | tr -d '\\n')
    elif [ -f "$HOME/.config/anthropic/api_key" ]; then
        export ANTHROPIC_API_KEY=$(cat "$HOME/.config/anthropic/api_key" | tr -d '\\n')
    fi
fi

# Python executable (prefer anaconda python3 with anthropic SDK)
PYTHON="${PYTHON:-/home/lkshpc/anaconda3/bin/python3}"

# Script path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPORT_SCRIPT="$SCRIPT_DIR/generate_work_report.py"

# Run the report generator in auto mode.
# Generate two reports: full (all work) and work-only (仿真/重建 via --topic 工作).
exec "$PYTHON" "$REPORT_SCRIPT" weekly --auto \
    && echo "[cron] Full report generated." \
    && "$PYTHON" "$REPORT_SCRIPT" weekly --auto --topic 工作 --output "$HOME/.agents/work-reports/$(date +%Y-%m)/weekly-$(date +%Y-%m-%d)-work.md" \
    && echo "[cron] Work-only report generated."
