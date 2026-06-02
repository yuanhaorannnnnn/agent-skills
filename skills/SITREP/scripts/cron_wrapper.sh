#!/usr/bin/env bash
# Cron wrapper for work-report weekly generation.
# Ensures environment is properly set before running the report generator.
# Generates: full report + work-only report + 钉钉周报 submission.

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
    if [ -f "$HOME/.anthropic_api_key" ]; then
        export ANTHROPIC_API_KEY=$(cat "$HOME/.anthropic_api_key" | tr -d '\\n')
    elif [ -f "$HOME/.config/anthropic/api_key" ]; then
        export ANTHROPIC_API_KEY=$(cat "$HOME/.config/anthropic/api_key" | tr -d '\\n')
    fi
fi

# Python executable (prefer anaconda python3 with anthropic SDK)
PYTHON="${PYTHON:-/home/yhr/anaconda3/bin/python3}"

# Script paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPORT_SCRIPT="$SCRIPT_DIR/generate_work_report.py"
SUBMIT_SCRIPT="$SCRIPT_DIR/submit_dingtalk_report.py"

# DeepSeek API config (same as Claude Code)
if [ -z "${ANTHROPIC_BASE_URL:-}" ]; then
    export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
fi
if [ -z "${ANTHROPIC_MODEL:-}" ]; then
    export ANTHROPIC_MODEL="deepseek-v4-pro[1m]"
fi

REPORT_DIR="$HOME/.agents/work-reports/$(date +%Y-%m)"
REPORT_DATE="$(date +%Y-%m-%d)"
FULL_REPORT="$REPORT_DIR/weekly-$REPORT_DATE.md"
WORK_REPORT="$REPORT_DIR/weekly-$REPORT_DATE-work.md"

echo "[cron] $(date): Starting weekly report generation..."

# Step 1: Generate full report
"$PYTHON" "$REPORT_SCRIPT" weekly --auto \
    && echo "[cron] Full report generated: $FULL_REPORT" \
    || { echo "[cron] Full report generation failed"; exit 1; }

# Step 2: Generate work-only report (仿真/重建 via --topic 工作)
"$PYTHON" "$REPORT_SCRIPT" weekly --auto --topic 工作 --output "$WORK_REPORT" \
    && echo "[cron] Work-only report generated: $WORK_REPORT" \
    || { echo "[cron] Work-only report generation failed"; exit 1; }

# Step 3: Submit work-only report to 钉钉周报
if [ -f "$SUBMIT_SCRIPT" ] && [ -f "$WORK_REPORT" ]; then
    echo "[cron] Submitting work report to 钉钉..."
    "$PYTHON" "$SUBMIT_SCRIPT" --report "$WORK_REPORT" \
        && echo "[cron] 钉钉周报 submitted successfully." \
        || echo "[cron] 钉钉周报 submission failed (reports still saved to disk)."
else
    echo "[cron] Skipping 钉钉 submission: script or report missing."
fi

echo "[cron] $(date): Weekly report generation complete."
