#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="$ROOT_DIR/skills"
RUNTIME_DIR="$HOME/.agents/skills"
MANIFEST="$ROOT_DIR/manifest.yaml"

mkdir -p "$RUNTIME_DIR"
ln -sfn "$ROOT_DIR/scripts" "$RUNTIME_DIR/scripts"

get_manifest_enabled() {
  local target="$1"
  if [ ! -f "$MANIFEST" ]; then
    echo "true"
    return
  fi
  awk -v name="$target" '
    BEGIN { in_block=0 }
    $1 == "-" && $2 == "name:" && $3 == name { in_block=1; next }
    in_block && $1 == "enabled:" { print $2; exit }
    in_block && $1 == "-" { in_block=0 }
  ' "$MANIFEST"
}

is_skill_enabled() {
  local target="$1"
  local enabled_val
  enabled_val="$(get_manifest_enabled "$target")"
  [ "$enabled_val" != "false" ]
}

cleanup_repo_links() {
  for existing_link in "$RUNTIME_DIR"/*; do
    [ -L "$existing_link" ] || continue
    local skill_name existing_target
    skill_name="$(basename "$existing_link")"
    existing_target="$(readlink "$existing_link" || true)"
    case "$existing_target" in
      "$SKILLS_DIR/"*)
        if [ ! -e "$existing_link" ] || [ ! -d "$SKILLS_DIR/$skill_name" ] || ! is_skill_enabled "$skill_name"; then
          rm -f "$existing_link"
          echo "Removed stale link: $skill_name"
        fi
        ;;
    esac
  done
}

cleanup_repo_links

installed=()
updated=()
skipped=()
missing_skillmd=()

for skill_dir in "$SKILLS_DIR"/*/; do
  [ -d "$skill_dir" ] || continue
  skill_name="$(basename "$skill_dir")"

  if [ ! -f "$skill_dir/SKILL.md" ]; then
    missing_skillmd+=("$skill_name")
    continue
  fi

  if ! is_skill_enabled "$skill_name"; then
    skipped+=("$skill_name (disabled in manifest)")
    continue
  fi

  target_link="$RUNTIME_DIR/$skill_name"
  if [ -L "$target_link" ]; then
    updated+=("$skill_name")
  else
    installed+=("$skill_name")
  fi
  ln -sfn "$skill_dir" "$target_link"
done

echo ""
echo "=== agent-skills install report ==="
if [ ${#installed[@]} -gt 0 ]; then
  echo "Installed: ${installed[*]}"
fi
if [ ${#updated[@]} -gt 0 ]; then
  echo "Updated:   ${updated[*]}"
fi
if [ ${#skipped[@]} -gt 0 ]; then
  echo "Skipped:   ${skipped[*]}"
fi
if [ ${#missing_skillmd[@]} -gt 0 ]; then
  echo "Missing SKILL.md: ${missing_skillmd[*]}"
fi
echo "==================================="
