#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Pulling latest changes..."
git -C "$ROOT_DIR" pull --ff-only

echo "Running install..."
bash "$ROOT_DIR/scripts/install.sh"
