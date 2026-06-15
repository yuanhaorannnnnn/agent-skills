#!/usr/bin/env bash
# Daily 8:00 download assigned work items
set -euo pipefail

LOG_DIR="$HOME/.claude/logs"
mkdir -p "$LOG_DIR"
exec >>"$LOG_DIR/yunxiao-download.log" 2>&1

export PATH="$HOME/.local/bin:$PATH"

if [ -f "$HOME/.bashrc" ]; then source "$HOME/.bashrc" 2>/dev/null || true; fi
if [ -z "${YUNXIAO_ACCESS_TOKEN:-}" ]; then
    DOTFILES_SECRETS="/media/yhr/2T/files/cc_projects/infra/scaffold/bash/secrets"
    if [ -f "$DOTFILES_SECRETS" ]; then
        source "$DOTFILES_SECRETS"
    fi
fi

PYTHON="${PYTHON:-/home/yhr/anaconda3/bin/python3}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "[yunxiao-download] $(date)"

max_attempts="${YUNXIAO_DOWNLOAD_ATTEMPTS:-5}"
sleep_seconds="${YUNXIAO_DOWNLOAD_RETRY_SLEEP:-60}"
rc=1
for attempt in $(seq 1 "$max_attempts"); do
    echo "[yunxiao-download] attempt $attempt/$max_attempts"
    if "$PYTHON" "$SCRIPT_DIR/download_workitems.py"; then
        exit 0
    fi
    rc=$?
    if [ "$attempt" -lt "$max_attempts" ]; then
        echo "[yunxiao-download] attempt $attempt failed rc=$rc; retrying in ${sleep_seconds}s"
        sleep "$sleep_seconds"
    fi
done

echo "[yunxiao-download] failed after ${max_attempts} attempts"
exit "$rc"
