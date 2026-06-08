---
name: Sentinel
description: |
  Cross-agent build and long-running command monitor. Use when the user wants to
  run a build, package, test, or other long-running command in a separate terminal
  while keeping an agent-readable log and state file. Trigger on requests like
  monitor build, 监控构建, 新终端启动并监控, package with monitoring, tail build logs,
  check build status, or when Repair Fix needs a self-check build/test monitor.

  Do NOT use for ordinary short shell commands. Do not start builds unless the user
  explicitly asks to build/test/package or the active workflow has already reached
  its verification step.
---

# Sentinel — Build/Command Monitor

Run long-running commands with a stable task id, human-visible terminal output, and agent-readable state.

## Command

Default to `run`: it starts the command in a separate terminal, then blocks the agent side until the command reaches a final status and returns a compact summary.

```bash
~/.agents/repos/agent-skills/skills/Sentinel/scripts/sentinel.sh run \
  --id <task-id> \
  --title "<window title>" \
  --cwd <workdir> \
  [--conda-env <name>] \
  [--conda-sh <path>] \
  [--env KEY=VALUE]... \
  [--env-file <path>] \
  [--lines 60] \
  -- <command...>
```

For tests or environments without a GUI terminal, add `--no-terminal`. Use `start` only when the user explicitly wants fire-and-forget behavior.

## Identity

A monitor target is defined by:

- `--id`: stable task identity for later status/tail/errors/stop calls
- `--cwd`: working directory where the command runs
- `-- <command...>`: command being monitored

State is stored under:

```text
/tmp/agent-sentinel/<id>/
  state.json
  build.log
  runner.sh
  command.json
```

Override root with `SENTINEL_ROOT` only for tests or controlled environments. `MONITOR_BUILD_ROOT` remains accepted by the compatibility wrapper.

## Query

```bash
sentinel.sh wait --id <task-id> --lines 60
sentinel.sh status --id <task-id>
sentinel.sh tail --id <task-id> --lines 80
sentinel.sh errors --id <task-id>
sentinel.sh stop --id <task-id>
```

`state.json` is the source of truth. Logs are evidence. `run` is `start + wait`: it does not stream logs to the agent, but it returns when the command succeeds, fails, stops, or becomes stale.

## Environment Rules

- No `--conda-env`: do not activate conda; inherit the launcher environment plus explicit env injection.
- With `--conda-env`: source conda and activate the named environment before running the command.
- `--env KEY=VALUE` and `--env-file <path>` are independent of conda.
- Do not print secrets or write env values to `state.json`; only store env keys and env-file paths.

## Status Rules

```text
created -> running -> succeeded | failed | stopped | stale
```

- `exit_code == 0`: `succeeded`
- `exit_code != 0`: `failed`
- no final status and process group no longer exists: `stale`
- `errors` scans logs for common error markers; it does not decide success/failure

## Repair Integration

Use in `Repair Fix` when build/test verification is part of the self-check. `Repair Closeout` should consume the resulting `self_check_summary` and deliverable links; it should not start a new build by itself.


## Workflow Gate Contract

Sentinel is verification infrastructure for workflow skills and follows the shared output contract:

```text
/home/yhr/.agents/repos/agent-skills/references/skill-output-contract.md
```

The caller skill owns durable Canon promotion. Sentinel owns runtime state, final status, compact log summary, and artifact paths.

## Gotchas

- Use `run` when the agent must wait for a final build/test result. `run` is `start + wait`; it blocks until `succeeded`, `failed`, `stopped`, or `stale`.
- Use `start` only for explicit fire-and-forget monitoring. If the workflow needs validation evidence, follow with `wait`.
- Do not treat `errors` output as final status. `state.json.status` and exit code decide success/failure.
- Do not put secrets into env logs or `state.json`; record env keys and env-file paths only.
- `Repair Closeout` and `Tasking Turnover` must not launch Sentinel builds; they consume prior Sentinel evidence.

## Canon 输出边界

读取共享契约：`/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md`。

- `/tmp/agent-sentinel/<id>/state.json` is the source of truth only for the active monitor task; it is runtime state, not durable project memory.
- Build logs, `command.json`, `runner.sh`, and final summaries are artifacts. Keep them under `SENTINEL_ROOT` and reference absolute paths from Canon when the result matters.
- For meaningful build/test outcomes, create or update `/media/yhr/2T/Canon/raw/update-cards/<date>-sentinel-<task-id>.md` or let the caller skill (`Repair`, `Tasking`, `Sweep`) promote the result.
- Failed builds that reveal reusable failure modes should become Canon `incidents/`; repeated build patterns can become Canon `patterns/` or `workflows/`.
