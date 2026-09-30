---
name: passdown
description: |
  Transfer context from a previous coding-agent session into the current one. Trigger on "handoff", "接手上下文", "agent交接", "继续上一个agent的对话", or a fresh conversation continuing focused work. Auto-detects runtime and defaults to the current directory; advanced selection loads only when needed.
---

# Agent Handoff

Like tmux attach for coding agents. Read a previous agent's raw JSONL session log, extract the essential user/assistant conversation, and inject it into the current context.

passdown transfers context, not workspace ownership. For durable context and artifacts, follow the shared Canon contract:

```text
/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md
```

## Core Rule

Transfer the conversation and relationship map, not the implementation files. The goal is to understand what the user was doing, what decisions were made, what artifacts matter, and what the next step is.

When the handoff target (交接对象) is a GPT model and the source (被交接对象) is DeepSeek or Gemini, enforce `review + passdown`: perform a read-only audit on the pending handoff content and evidence before completing the handoff.

## Minimal entry

For same-directory handoff, run:

```bash
python3 <skill-dir>/scripts/extract_handoff.py --focus "<topic>" --json
```

When the source directory/runtime/session is specified, for fresh-conversation
rollover, for optional archival, or for DeepSeek/Gemini → GPT handoff, read
[mode routing and review contract](references/modes.md) before acting.
The latter requires read-only Review + Passdown, not transcript extraction alone.
Read [runtime quirks](references/runtime-quirks.md) only when discovery or parsing
needs runtime-specific handling.

## Non-Negotiable Constraints

- **Read-only on source side.** Never write to or delete another agent's session
  storage. Conversation archival, when the mode routing contract permits it, is a
  runtime lifecycle operation, not a session-file edit.
- **Artifacts by reference.** In cross-directory handoff, artifacts remain owned by the source workspace. Use absolute paths. Do not copy `.planning`, `.proposal`, `.research`, `.agent-state`, build outputs, logs, images, tarballs, or reports unless the user explicitly asks for a portable bundle.
- **Filter aggressively.** Keep only user messages and assistant core replies. Drop tool call arguments, tool results, system/developer prompts, guardian/judge subflows, token logs, and raw system dumps.
- **Respect token budget.** Enforce the extractor's hard token budget. Prefer recent turns, initial context, focus hits, explicit decisions, and next steps.
- **Always show what you learned.** Present source agent, source cwd, current cwd, session file, candidate count, turn count, token estimate, key decisions, artifacts, pending work, and next step.

## Workflow

### Step 1: Identify source agent, source workspace, and focus

If user gives another directory, use it as the source workspace even if the current shell is elsewhere.

Examples:

```text
/passdown --former claude --dir /path/to/CarlaUE5 --focus "JHBN-7679"
/passdown --former codex --dir /path/to/agent-skills --focus "Canon migration"
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
- **DSH**: `ls -t ~/.dsh/sessions/--<cwd-with-dashes>--/`; each subdirectory is a session id holding `session.jsonl.zstd`.

Then rerun with `--file`.

### Step 3: Extract, filter, and compress

The extractor handles:

- Codex TRANSCRIPT mode for guardian-wrapped sessions
- Codex direct mode fallback
- Pi message JSONL
- Claude Code project JSONL
- DSH zstd-compressed session JSONL
- focus-ranked candidate selection
- optional zvec-backed candidate retrieval for focused queries

The extractor enforces `--max-tokens` before returning JSON. When compressing
the selected turns into the final handoff, keep:

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

### Step 4b: Review Gate for DeepSeek/Gemini source (Review + Passdown)

When handing off from DeepSeek or Gemini to a GPT model, do not proceed directly from the extracted transcript to execution. Perform a read-only evidence audit:

- **Direct code/runtime evidence**: Check whether claimed test results or metrics actually exist on disk and were produced by verified runs (e.g. check logs, output images, exit codes).
- **Hypothesis boundary**: Flag claims that were derived from LLM code reading rather than physical/dynamic runs (e.g. static configuration differences vs dynamic runtime causes).
- **Metric bugs & traps**: Check for uncalibrated baselines, missing warmup frames, or bad geometric fits in source scripts.

Record findings under `## Review Gate Findings`. Downgrade any unverified causal claim to an open hypothesis before formatting the final handoff.

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

## Review Gate Findings (when Review + Passdown applies)

## Artifact Map

## Current Next Step
```

### Step 6: Same-runtime archival (optional)

After presenting the handoff, if this was a same-runtime rollover and the
archival contract in `references/modes.md` permits it, archive the source conversation and report
the archived source session id plus the successor id. Otherwise leave the source
untouched and state why.

### Step 7: Canon promotion

If the handoff establishes durable context, create or update a Canon update card under:

```text
/media/yhr/2T/Canon/raw/update-cards/
```

Promote stable facts into Canon task/project/decision/pattern/incident pages only when the durable target is clear. If not clear, keep the update card as the ingest bridge.
