#!/usr/bin/env bash
set -euo pipefail

ROOT="${SENTINEL_ROOT:-${MONITOR_BUILD_ROOT:-/tmp/agent-sentinel}}"
SCRIPT_SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"

usage() {
  cat <<'USAGE_EOF'
Usage:
  sentinel.sh run --id <id> [start options] [--lines N] -- <command...>
  sentinel.sh start --id <id> [--title <title>] [--cwd <dir>] [--terminal auto|name] [--no-terminal] [--wait] [--log-mode overwrite|append] [--conda-env <name>] [--conda-sh <path>] [--env KEY=VALUE]... [--env-file <path>] -- <command...>
  sentinel.sh wait --id <id> [--lines N]
  sentinel.sh status --id <id>
  sentinel.sh tail --id <id> [--lines N]
  sentinel.sh errors --id <id>
  sentinel.sh stop --id <id>
USAGE_EOF
}

fail() {
  echo "error: $*" >&2
  exit 2
}

sanitize_id() {
  local id="$1"
  [[ -n "$id" ]] || fail "--id is required"
  [[ "$id" =~ ^[A-Za-z0-9._-]+$ ]] || fail "--id may contain only letters, digits, dot, underscore, and hyphen"
}

task_dir() { printf '%s/%s' "$ROOT" "$1"; }
state_file() { printf '%s/state.json' "$(task_dir "$1")"; }
log_file() { printf '%s/build.log' "$(task_dir "$1")"; }
runner_file() { printf '%s/runner.sh' "$(task_dir "$1")"; }
command_file() { printf '%s/command.json' "$(task_dir "$1")"; }

json_init() {
  local id="$1" title="$2" cwd="$3" log_mode="$4" conda_env="$5" conda_sh="$6" terminal="$7" no_terminal="$8" wait_mode="$9"
  shift 9
  local env_json="$1" env_files_json="$2" command_json="$3"
  mkdir -p "$(task_dir "$id")"
  umask 077
  printf '%s\n' "$command_json" > "$(command_file "$id")"
  TASK_ID="$id" TITLE="$title" CWD_VALUE="$cwd" LOG_PATH="$(log_file "$id")" RUNNER_PATH="$(runner_file "$id")" \
  LOG_MODE="$log_mode" CONDA_ENV_VALUE="$conda_env" CONDA_SH_VALUE="$conda_sh" TERMINAL_VALUE="$terminal" \
  NO_TERMINAL_VALUE="$no_terminal" WAIT_VALUE="$wait_mode" ENV_JSON="$env_json" ENV_FILES_JSON="$env_files_json" COMMAND_JSON="$command_json" \
  STATE_PATH="$(state_file "$id")" \
  python3 - <<'PY'
import json, os
from datetime import datetime, timezone
state = {
    "id": os.environ["TASK_ID"],
    "title": os.environ["TITLE"],
    "cwd": os.environ["CWD_VALUE"],
    "command": json.loads(os.environ["COMMAND_JSON"]),
    "status": "created",
    "pid": None,
    "pgid": None,
    "exit_code": None,
    "started_at": None,
    "ended_at": None,
    "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "log_path": os.environ["LOG_PATH"],
    "runner_path": os.environ["RUNNER_PATH"],
    "log_mode": os.environ["LOG_MODE"],
    "conda_env": os.environ["CONDA_ENV_VALUE"] or None,
    "conda_sh": os.environ["CONDA_SH_VALUE"] or None,
    "terminal": os.environ["TERMINAL_VALUE"],
    "no_terminal": os.environ["NO_TERMINAL_VALUE"] == "1",
    "wait": os.environ["WAIT_VALUE"] == "1",
    "env_keys": [item.split("=", 1)[0] for item in json.loads(os.environ["ENV_JSON"])],
    "env_files": json.loads(os.environ["ENV_FILES_JSON"]),
}
with open(os.environ["STATE_PATH"], "w", encoding="utf-8") as f:
    json.dump(state, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY
}

json_update() {
  local id="$1" status="$2" pid="${3:-}" pgid="${4:-}" exit_code="${5:-}"
  TASK_ID="$id" STATUS_VALUE="$status" PID_VALUE="$pid" PGID_VALUE="$pgid" EXIT_CODE_VALUE="$exit_code" STATE_PATH="$(state_file "$id")" \
  python3 - <<'PY'
import json, os
from datetime import datetime, timezone
path = os.environ["STATE_PATH"]
with open(path, encoding="utf-8") as f:
    state = json.load(f)
status = os.environ["STATUS_VALUE"]
state["status"] = status
if os.environ["PID_VALUE"]:
    state["pid"] = int(os.environ["PID_VALUE"])
if os.environ["PGID_VALUE"]:
    state["pgid"] = int(os.environ["PGID_VALUE"])
if os.environ["EXIT_CODE_VALUE"]:
    state["exit_code"] = int(os.environ["EXIT_CODE_VALUE"])
now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
if status == "running" and not state.get("started_at"):
    state["started_at"] = now
if status in {"succeeded", "failed", "stopped", "stale"}:
    state["ended_at"] = now
with open(path, "w", encoding="utf-8") as f:
    json.dump(state, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY
}

maybe_mark_stale() {
  local id="$1" sf pgid status
  sf="$(state_file "$id")"
  [[ -f "$sf" ]] || return 0
  read -r status pgid < <(STATE_PATH="$sf" python3 - <<'PY'
import json, os
with open(os.environ["STATE_PATH"], encoding="utf-8") as f:
    s = json.load(f)
print(s.get("status"), s.get("pgid") or "")
PY
)
  if [[ "$status" == "running" && -n "$pgid" ]]; then
    if ! kill -0 "-$pgid" 2>/dev/null; then
      json_update "$id" "stale" "" "" ""
    fi
  fi
}

print_status() {
  local id="$1"
  sanitize_id "$id"
  local sf="$(state_file "$id")"
  [[ -f "$sf" ]] || fail "unknown monitor id: $id"
  maybe_mark_stale "$id"
  cat "$sf"
}

quote_array_items() {
  local item
  for item in "$@"; do
    printf '%q ' "$item"
  done
}

json_array() {
  python3 - "$@" <<'PY'
import json, sys
print(json.dumps(sys.argv[1:], ensure_ascii=False))
PY
}

make_runner() {
  local id="$1" cwd="$2" log_mode="$3" conda_env="$4" conda_sh="$5"
  shift 5
  local -a env_items=( ) env_files=( ) cmd=( )
  local mode="env"
  while (($#)); do
    case "$1" in
      --env-items-end) mode="env_files"; shift ;;
      --env-files-end) mode="cmd"; shift ;;
      *)
        if [[ "$mode" == "env" ]]; then env_items+=("$1");
        elif [[ "$mode" == "env_files" ]]; then env_files+=("$1");
        else cmd+=("$1"); fi
        shift ;;
    esac
  done
  local runner="$(runner_file "$id")" log="$(log_file "$id")"
  {
    printf '#!/usr/bin/env bash\n'
    printf 'set -u\nset -o pipefail\n'
    printf 'cd %q || exit 125\n' "$cwd"
    printf 'mkdir -p %q\n' "$(task_dir "$id")"
    if [[ "$log_mode" == "overwrite" ]]; then
      printf ': > %q\n' "$log"
    fi
    printf 'pid=$$\n'
    printf 'pgid=$(ps -o pgid= $$ | tr -d " ")\n'
    printf '%q _mark-running --id %q --pid "$pid" --pgid "$pgid"\n' "$SCRIPT_SELF" "$id"
    for f in "${env_files[@]}"; do
      printf 'set -a\nsource %q\nset +a\n' "$f"
    done
    for e in "${env_items[@]}"; do
      local key="${e%%=*}"
      local value="${e#*=}"
      printf 'export %q=%q\n' "$key" "$value"
    done
    if [[ -n "$conda_env" ]]; then
      printf 'set +u\n'
      if [[ -n "$conda_sh" ]]; then
        printf 'source %q || { rc=$?; set -u; echo "error: failed to source conda file" | tee -a %q; %q _finish --id %q --exit-code 126; exit 126; }\n' "$conda_sh" "$log" "$SCRIPT_SELF" "$id"
      else
        printf 'conda_base=$(conda info --base 2>/dev/null) || { rc=$?; set -u; echo "error: conda not found" | tee -a %q; %q _finish --id %q --exit-code 126; exit 126; }\n' "$log" "$SCRIPT_SELF" "$id"
        printf 'source "$conda_base/etc/profile.d/conda.sh" || { rc=$?; set -u; echo "error: failed to source conda.sh" | tee -a %q; %q _finish --id %q --exit-code 126; exit 126; }\n' "$log" "$SCRIPT_SELF" "$id"
      fi
      printf 'conda activate %q || { rc=$?; set -u; echo "error: failed to activate conda env: %s" | tee -a %q; %q _finish --id %q --exit-code 126; exit 126; }\n' "$conda_env" "$conda_env" "$log" "$SCRIPT_SELF" "$id"
      printf 'set -u\n'
    fi
    printf 'cmd=( %s)\n' "$(quote_array_items "${cmd[@]}")"
    printf '"${cmd[@]}" 2>&1 | tee -a %q\n' "$log"
    printf 'rc=${PIPESTATUS[0]}\n'
    printf 'echo "EXIT_CODE=$rc" | tee -a %q\n' "$log"
    printf '%q _finish --id %q --exit-code "$rc"\n' "$SCRIPT_SELF" "$id"
    printf 'echo "=== Done (exit: $rc) ==="\n'
    printf 'exit "$rc"\n'
  } > "$runner"
  chmod +x "$runner"
}

detect_terminal() {
  local requested="$1"
  if [[ "$requested" != "auto" ]]; then
    command -v "$requested" >/dev/null 2>&1 || fail "terminal not found: $requested"
    echo "$requested"
    return
  fi
  local t
  for t in ghostty gnome-terminal konsole kitty alacritty wezterm xterm; do
    if command -v "$t" >/dev/null 2>&1; then
      echo "$t"
      return
    fi
  done
  fail "no supported terminal found; pass --no-terminal"
}

launch_terminal() {
  local terminal="$1" title="$2" runner="$3"
  case "$terminal" in
    ghostty) ghostty --title="$title" -e bash -lc "$runner; echo; read -r -p 'Press Enter to close...'" & ;;
    gnome-terminal) gnome-terminal --title="$title" -- bash -lc "$runner; echo; read -r -p 'Press Enter to close...'" & ;;
    konsole) konsole --new-tab -p tabtitle="$title" -e bash -lc "$runner; echo; read -r -p 'Press Enter to close...'" & ;;
    kitty) kitty --title "$title" bash -lc "$runner; echo; read -r -p 'Press Enter to close...'" & ;;
    alacritty) alacritty --title "$title" -e bash -lc "$runner; echo; read -r -p 'Press Enter to close...'" & ;;
    wezterm) wezterm start -- bash -lc "$runner; echo; read -r -p 'Press Enter to close...'" & ;;
    xterm) xterm -T "$title" -e bash -lc "$runner; echo; read -r -p 'Press Enter to close...'" & ;;
    *) fail "unsupported terminal: $terminal" ;;
  esac
}

cmd_start() {
  local id="" title="Build" cwd="$PWD" terminal="auto" no_terminal=0 wait_mode=0 log_mode="overwrite" conda_env="" conda_sh=""
  local -a env_items=( ) env_files=( ) cmd=( )
  while (($#)); do
    case "$1" in
      --id) id="${2:-}"; shift 2 ;;
      --title) title="${2:-}"; shift 2 ;;
      --cwd) cwd="${2:-}"; shift 2 ;;
      --terminal) terminal="${2:-}"; shift 2 ;;
      --no-terminal) no_terminal=1; shift ;;
      --wait) wait_mode=1; shift ;;
      --log-mode) log_mode="${2:-}"; shift 2 ;;
      --conda-env) conda_env="${2:-}"; shift 2 ;;
      --conda-sh) conda_sh="${2:-}"; shift 2 ;;
      --env) env_items+=("${2:-}"); shift 2 ;;
      --env-file) env_files+=("${2:-}"); shift 2 ;;
      --) shift; cmd=("$@"); break ;;
      -h|--help) usage; exit 0 ;;
      *) fail "unknown start option: $1" ;;
    esac
  done
  sanitize_id "$id"
  [[ -d "$cwd" ]] || fail "--cwd does not exist: $cwd"
  [[ "$log_mode" == "overwrite" || "$log_mode" == "append" ]] || fail "--log-mode must be overwrite or append"
  ((${#cmd[@]} > 0)) || fail "command is required after --"
  local e
  for e in "${env_items[@]}"; do
    [[ "$e" == *=* ]] || fail "--env must be KEY=VALUE: $e"
    [[ "${e%%=*}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || fail "invalid env key: ${e%%=*}"
  done
  local f
  for f in "${env_files[@]}"; do
    [[ -f "$f" ]] || fail "--env-file not found: $f"
  done

  local env_json env_files_json cmd_json
  env_json="$(json_array "${env_items[@]}")"
  env_files_json="$(json_array "${env_files[@]}")"
  cmd_json="$(json_array "${cmd[@]}")"
  json_init "$id" "$title" "$cwd" "$log_mode" "$conda_env" "$conda_sh" "$terminal" "$no_terminal" "$wait_mode" "$env_json" "$env_files_json" "$cmd_json"
  make_runner "$id" "$cwd" "$log_mode" "$conda_env" "$conda_sh" "${env_items[@]}" --env-items-end "${env_files[@]}" --env-files-end "${cmd[@]}"

  if [[ "$no_terminal" == "1" ]]; then
    if [[ "$wait_mode" == "1" ]]; then
      "$(runner_file "$id")"
    else
      setsid "$(runner_file "$id")" >/dev/null 2>&1 &
      echo "ID=$id"
      echo "STATE=$(state_file "$id")"
      echo "LOG=$(log_file "$id")"
    fi
  else
    local term
    term="$(detect_terminal "$terminal")"
    launch_terminal "$term" "$title" "$(runner_file "$id")"
    echo "ID=$id"
    echo "STATE=$(state_file "$id")"
    echo "LOG=$(log_file "$id")"
  fi
}

state_value() {
  local id="$1" key="$2"
  STATE_PATH="$(state_file "$id")" STATE_KEY="$key" python3 - <<'PY'
import json, os
with open(os.environ["STATE_PATH"], encoding="utf-8") as f:
    state = json.load(f)
value = state.get(os.environ["STATE_KEY"])
if value is None:
    print("")
else:
    print(value)
PY
}

print_final_summary() {
  local id="$1" lines="$2"
  local sf lf status exit_code
  sf="$(state_file "$id")"
  lf="$(log_file "$id")"
  status="$(state_value "$id" status)"
  exit_code="$(state_value "$id" exit_code)"
  echo "STATUS=$status"
  echo "EXIT_CODE=$exit_code"
  echo "STATE=$sf"
  echo "LOG=$lf"
  echo
  echo "--- tail ---"
  if [[ -f "$lf" ]]; then
    tail -n "$lines" "$lf"
  fi
  echo
  echo "--- errors ---"
  if [[ -f "$lf" ]]; then
    grep -Ein '(^|[^A-Za-z])(error:|fatal:|failed|failure|exception|traceback|undefined reference|segmentation fault)' "$lf" || true
  fi
}

cmd_wait() {
  local id="" lines="60"
  while (($#)); do
    case "$1" in
      --id) id="${2:-}"; shift 2 ;;
      --lines) lines="${2:-}"; shift 2 ;;
      *) fail "unknown wait option: $1" ;;
    esac
  done
  sanitize_id "$id"
  [[ "$lines" =~ ^[0-9]+$ ]] || fail "--lines must be a number"
  local sf="$(state_file "$id")"
  [[ -f "$sf" ]] || fail "unknown monitor id: $id"

  while true; do
    maybe_mark_stale "$id"
    local status pgid pid
    status="$(state_value "$id" status)"
    case "$status" in
      succeeded|failed|stopped|stale) break ;;
    esac
    pgid="$(state_value "$id" pgid)"
    pid="$(state_value "$id" pid)"
    if [[ -n "$pid" ]]; then
      tail --pid="$pid" -f /dev/null 2>/dev/null || sleep 1
    elif [[ -n "$pgid" ]]; then
      while kill -0 "-$pgid" 2>/dev/null; do sleep 1; done
    else
      sleep 1
    fi
  done

  print_final_summary "$id" "$lines"
  local exit_code
  exit_code="$(state_value "$id" exit_code)"
  if [[ -n "$exit_code" ]]; then
    return "$exit_code"
  fi
  case "$(state_value "$id" status)" in
    succeeded) return 0 ;;
    failed|stopped|stale) return 1 ;;
    *) return 2 ;;
  esac
}

cmd_run() {
  local id="" lines="60"
  local -a start_args=( )
  while (($#)); do
    case "$1" in
      --id) id="${2:-}"; start_args+=("$1" "${2:-}"); shift 2 ;;
      --lines) lines="${2:-}"; shift 2 ;;
      --) shift; start_args+=("--" "$@"); break ;;
      *)
        start_args+=("$1")
        if [[ $# -gt 1 && "$2" != --* ]]; then
          start_args+=("$2")
          shift 2
        else
          shift
        fi
        ;;
    esac
  done
  sanitize_id "$id"
  cmd_start "${start_args[@]}"
  cmd_wait --id "$id" --lines "$lines"
}

cmd_tail() {
  local id="" lines="80"
  while (($#)); do
    case "$1" in
      --id) id="${2:-}"; shift 2 ;;
      --lines) lines="${2:-}"; shift 2 ;;
      *) fail "unknown tail option: $1" ;;
    esac
  done
  sanitize_id "$id"
  [[ "$lines" =~ ^[0-9]+$ ]] || fail "--lines must be a number"
  local lf="$(log_file "$id")"
  [[ -f "$lf" ]] || fail "log not found for monitor id: $id"
  tail -n "$lines" "$lf"
}

cmd_errors() {
  local id=""
  while (($#)); do
    case "$1" in
      --id) id="${2:-}"; shift 2 ;;
      *) fail "unknown errors option: $1" ;;
    esac
  done
  sanitize_id "$id"
  local lf="$(log_file "$id")"
  [[ -f "$lf" ]] || fail "log not found for monitor id: $id"
  grep -Ein '(^|[^A-Za-z])(error:|fatal:|failed|failure|exception|traceback|undefined reference|segmentation fault)' "$lf" || true
}

cmd_stop() {
  local id=""
  while (($#)); do
    case "$1" in
      --id) id="${2:-}"; shift 2 ;;
      *) fail "unknown stop option: $1" ;;
    esac
  done
  sanitize_id "$id"
  local sf="$(state_file "$id")"
  [[ -f "$sf" ]] || fail "unknown monitor id: $id"
  local pgid
  pgid="$(STATE_PATH="$sf" python3 - <<'PY'
import json, os
with open(os.environ["STATE_PATH"], encoding="utf-8") as f:
    print(json.load(f).get("pgid") or "")
PY
)"
  if [[ -n "$pgid" ]] && kill -0 "-$pgid" 2>/dev/null; then
    kill -TERM "-$pgid" 2>/dev/null || true
  fi
  json_update "$id" "stopped" "" "" ""
}

case "${1:-}" in
  run) shift; cmd_run "$@" ;;
  start) shift; cmd_start "$@" ;;
  status)
    shift
    id=""
    while (($#)); do
      case "$1" in --id) id="${2:-}"; shift 2 ;; *) fail "unknown status option: $1" ;; esac
    done
    print_status "$id"
    ;;
  wait) shift; cmd_wait "$@" ;;
  tail) shift; cmd_tail "$@" ;;
  errors) shift; cmd_errors "$@" ;;
  stop) shift; cmd_stop "$@" ;;
  _mark-running)
    shift
    id=""; pid=""; pgid=""
    while (($#)); do
      case "$1" in --id) id="${2:-}"; shift 2 ;; --pid) pid="${2:-}"; shift 2 ;; --pgid) pgid="${2:-}"; shift 2 ;; *) fail "unknown _mark-running option: $1" ;; esac
    done
    json_update "$id" "running" "$pid" "$pgid" ""
    ;;
  _finish)
    shift
    id=""; exit_code=""
    while (($#)); do
      case "$1" in --id) id="${2:-}"; shift 2 ;; --exit-code) exit_code="${2:-}"; shift 2 ;; *) fail "unknown _finish option: $1" ;; esac
    done
    if [[ "$exit_code" == "0" ]]; then json_update "$id" "succeeded" "" "" "$exit_code"; else json_update "$id" "failed" "" "" "$exit_code"; fi
    ;;
  -h|--help|"") usage ;;
  *) fail "unknown command: $1" ;;
esac
