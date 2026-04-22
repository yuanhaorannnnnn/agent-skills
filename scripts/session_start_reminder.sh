#!/usr/bin/env bash
# Session start reminder: detect active conversation and suggest restore

set -euo pipefail

REPO=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
if [[ -z "$REPO" ]]; then
    REPO="$(pwd)"
fi

STATE_DIR="$REPO/.agent-state"
ACTIVE_FILE="$STATE_DIR/ACTIVE_CONVERSATION"

if [[ -f "$ACTIVE_FILE" ]]; then
    CONVERSATION=$(tr -d '\n' < "$ACTIVE_FILE")
    CONV_FILE="$STATE_DIR/conversations/${CONVERSATION}.md"
    if [[ -f "$CONV_FILE" ]]; then
        echo "{\"systemMessage\": \"💡 检测到活动 conversation: ${CONVERSATION}。如需恢复工作状态，请执行 /restore --conversation ${CONVERSATION}\"}"
        exit 0
    fi
fi

echo "{\"systemMessage\": \"💡 如需恢复之前的工作状态，请执行 /restore --conversation \u003cname\u003e\"}"
