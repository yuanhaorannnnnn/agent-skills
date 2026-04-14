#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="$ROOT_DIR/agent-platform/skills"
RUNTIME_DIR="$HOME/.agents/skills"

mkdir -p "$RUNTIME_DIR"

for existing_link in "$RUNTIME_DIR"/*; do
  [ -L "$existing_link" ] || continue
  existing_target="$(readlink "$existing_link" || true)"
  case "$existing_target" in
    "$SKILLS_DIR/"*)
      if [ ! -e "$existing_link" ]; then
        rm -f "$existing_link"
      fi
      ;;
  esac
done

find "$SKILLS_DIR" -mindepth 1 -maxdepth 1 -type d | while read -r skill_dir; do
  [ -f "$skill_dir/SKILL.md" ] || continue
  skill_name="$(basename "$skill_dir")"
  ln -sfn "$skill_dir" "$RUNTIME_DIR/$skill_name"
done

echo "Linked published skills into ~/.agents/skills"
