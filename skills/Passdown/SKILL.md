---
name: Passdown
description: |
  Transfer context from another coding agent session into the current session.
  Auto-detects runtime (Codex/Pi/Claude Code). Defaults to current directory —
  no parameters needed for same-repo handoff. Multi-runtime sessions merged by
  recency with focus filtering and deduplication.

  Trigger on: "agent handoff", "handoff", "接手上下文", "agent交接",
  "上下文切换", "attach session", "继续上一个agent的对话",
  "上次在这个目录做了什么".
---

# Agent Handoff

Like tmux attach for coding agents. Read a previous agent's raw JSONL session log, extract the essential user/assistant conversation, and inject it into the current context.

Passdown transfers context, not workspace ownership. For durable context and artifacts, follow the shared Canon contract:

```text
/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md
```

## Core Rule

Transfer the conversation and relationship map, not the implementation files. The goal is to understand what the user was doing, what decisions were made, what artifacts matter, and what the next step is.

## Modes

`--former` is optional. When omitted, auto-detects sessions from all three runtimes (Codex + Pi + Claude Code) and merges by recency.

`--dir` defaults to current working directory when not specified.

### Same-directory handoff（最简）

```bash
python3 <skill-dir>/scripts/extract_handoff.py --focus "<topic>" --json
```

Auto-detect runtime, default to current cwd.

### Cross-directory handoff

```bash
python3 <skill-dir>/scripts/extract_handoff.py --dir /absolute/source/workspace --focus "<topic>" --json
```

Auto-detect runtime in given directory.

### Specific runtime(s)

```bash
python3 <skill-dir>/scripts/extract_handoff.py --former claude --dir /absolute/workspace --focus "<topic>" --json
```

### Multi-runtime / multi-directory

```bash
# Scan both Claude Code and Codex sessions across two workspaces
python3 <skill-dir>/scripts/extract_handoff.py --former claude,codex --dir /project/a --dir /project/b --json

# Scan all runtimes across multiple directories
python3 <skill-dir>/scripts/extract_handoff.py --dir /project/a,/project/b,/project/c --json
```


### zvec-backed focused retrieval

zvec is integrated as a candidate retriever only. It changes how matching session files are found; it does not change parsing, compression, handoff format, or the original JSONL source of truth.

```bash
# Build/rebuild the local zvec index for the current workspace
python3 <skill-dir>/scripts/zvec_index.py --dir "$PWD" --rebuild

# Query through Passdown. auto uses zvec for focused queries when available,
# then falls back to the legacy keyword/mtime retriever.
python3 <skill-dir>/scripts/extract_handoff.py --dir "$PWD" --focus "<topic>" --retriever auto --json

# Force zvec. Fails if the index is missing or has no candidate.
python3 <skill-dir>/scripts/extract_handoff.py --dir "$PWD" --focus "<topic>" --retriever zvec --json
```

Index location defaults to `~/.agents/passdown-zvec-index`. Override with `PASSDOWN_ZVEC_PATH=/path/to/index`.

### Direct session file

```bash
python3 <skill-dir>/scripts/extract_handoff.py --file /absolute/session.jsonl --former claude --json
```

## Parameters

- `--former <codex|pi|claude,...>` — optional, comma-separated. Auto-detect from all three runtimes if omitted. Multi-runtime matches sorted by mtime desc.
- `--dir <path>` — optional, repeatable. Accepts multiple paths via `--dir /a --dir /b` or `--dir /a,/b`. Defaults to current working directory.
- `--file <path>` — direct session JSONL path; bypass discovery.
- `--focus "<topic>"` — find ALL matching sessions across runtimes. Extracts and deduplicates turns from every session with a non-zero focus score.
- `--retriever <auto|keyword|zvec>` — candidate retrieval mode. `auto` uses zvec for focused queries when an index exists, then falls back to keyword/mtime; `zvec` is strict; `keyword` preserves legacy behavior.

## Non-Negotiable Constraints

- **Read-only on source side.** Never write to another agent's session storage.
- **Artifacts by reference.** In cross-directory handoff, artifacts remain owned by the source workspace. Use absolute paths. Do not copy `.planning`, `.proposal`, `.research`, `.agent-state`, build outputs, logs, images, tarballs, or reports unless the user explicitly asks for a portable bundle.
- **Filter aggressively.** Keep only user messages and assistant core replies. Drop tool call arguments, tool results, system/developer prompts, guardian/judge subflows, token logs, and raw system dumps.
- **Respect token budget.** Cap the extracted conversation at ~8000 words. Prefer recent turns and focus-relevant turns when truncating.
- **Always show what you learned.** Present source agent, source cwd, current cwd, session file, candidate count, turn count, token estimate, key decisions, artifacts, pending work, and next step.

## Workflow

### Step 1: Identify source agent, source workspace, and focus

If user gives another directory, use it as the source workspace even if the current shell is elsewhere.

Examples:

```text
/Passdown --former claude --dir /media/yhr/2T/CarlaUE5 --focus "JHBN-7679"
/Passdown --former codex --dir /home/yhr/.agents/repos/agent-skills --focus "Canon migration"
```

### Step 2: Run extractor

```bash
python3 <skill-dir>/scripts/extract_handoff.py --former <agent> --dir <source-workspace> --focus "<topic>" --json
```

If no source directory was specified, use current cwd as `--cwd`.

If the extractor returns `No session found`, manually locate the session:

- **Claude Code**: `ls ~/.claude/projects/-<slug>/*.jsonl`, where slug replaces `/` and `_` with `-`.
- **Codex**: `find ~/.codex/sessions -name "*.jsonl" | sort` then inspect cwd/focus.
- **Pi**: `ls -t ~/.pi/agent/sessions/--<cwd-with-dashes>--/`.

Then rerun with `--file`.

### Step 3: Extract, filter, and compress

The extractor handles:

- Codex TRANSCRIPT mode for guardian-wrapped sessions
- Codex direct mode fallback
- Pi message JSONL
- Claude Code project JSONL
- focus-ranked candidate selection
- optional zvec-backed candidate retrieval for focused queries

When compressing manually, keep:

1. first 1-2 turns for initial context
2. last 3 turns for current state
3. focus-relevant turns
4. explicit decisions, approvals, rejected options, and next steps

Drop tool execution noise, repeated clarifications, and raw system/developer text.

### Step 4: Build artifact map

For same-directory and cross-directory handoff, produce an artifact map when paths are visible in the transcript or standard workspace files:

```text
Source workspace: /absolute/source/workspace
Current workspace: /absolute/current/workspace

Relevant artifacts:
- /absolute/source/.planning/... — runtime plan, referenced only
- /absolute/source/.proposal/... — proposal/report artifact, referenced only
- /absolute/source/.agent-state/... — runtime recap, referenced only
- /media/yhr/2T/Canon/tasks/... — durable task page when present
- /media/yhr/2T/Canon/raw/update-cards/... — ingest/update card when present
```

Do not read or inline large artifacts unless needed for the immediate next step. Prefer an index first.

### Step 5: Format handoff

For short sessions (<15 turns), include the full filtered transcript. For long sessions, include first 2 turns, last 3 turns, focus-relevant decisions, and a compact summary.

Use this structure:

```markdown
## Agent Handoff — <source agent> session

Source workspace: `<source cwd>`
Current workspace: `<current cwd>`
Focus: `<focus or none>`
Session file: `<path>`
Extracted turns: `<N>`

[... transcript or compressed transcript ...]

## Key Decisions

## Artifact Map

## Current Next Step
```

### Step 6: Canon promotion

If the handoff establishes durable context, create or update a Canon update card under:

```text
/media/yhr/2T/Canon/raw/update-cards/
```

Promote stable facts into Canon task/project/decision/pattern/incident pages only when the durable target is clear. If not clear, keep the update card as the ingest bridge.

## Agent-Specific Quirks

- **Codex guardian-wrapped sessions**: The real conversation is often in `>>> TRANSCRIPT` blocks inside `user_message` / `input_text`, not assistant `output_text`.
- **Codex sessions are per-rollout**: Multiple JSONL files may exist per day. Use cwd first, then focus score, then recency.
- **Pi**: Sessions are keyed by working directory. If multiple sessions exist, focus score ranks them before recency.
- **Claude Code slug**: Project directory slug replaces both `/` and `_` with `-`.
- **Same-runtime handoff**: Claude→Claude, Codex→Codex, Pi→Pi are valid. The source session JSONL may still be live; read only.
