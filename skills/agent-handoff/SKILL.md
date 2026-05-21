---
name: agent-handoff
description: |
  Transfer raw conversation context from another coding agent (Codex, Pi,
  Claude Code) into the current session. Like tmux attach for coding agents —
  no pre-processing, no save/export needed on the source side. Reads the
  source agent's persistent JSONL session log directly.

  Trigger on: "agent handoff", "handoff from codex", "接手 codex 的上下文",
  "从 pi 切换过来", "继续 codex 的会话", "handoff from pi",
  "switch from claude", "agent交接", "上下文切换", "接管会话",
  "attach codex session", "继续上一个agent的对话".
---

# Agent Handoff

Like tmux attach for coding agents. Read the previous agent's raw JSONL
session log, extract the essential user/assistant conversation, and inject
it into the current context — no pre-processing needed on the source side.

## Core Rule

Transfer the conversation, not the implementation. The goal is for you to
understand what the user was doing, what decisions were made, and what's
the next step — not to replay every tool call and system message.

## Non-Negotiable Constraints

- **Read-only on the source side.** Never write to another agent's session storage.
- **Filter aggressively.** Keep only user messages and assistant core replies.
  Drop: tool call arguments, tool results, system messages, internal agent
  sub-flows (guardian, judge, etc.), repeated system prompts, token count logs.
- **Respect token budget.** Cap the extracted conversation at ~8000 words.
  Prefer recent turns over earlier ones when truncating.
- **Always show what you learned.** After extraction, present:
  - Source agent, session time, turn count, token estimate.
  - Key decisions made in the source session.
  - Current pending work / next step.
  - For short sessions (<15 turns): include the full filtered transcript.
  - For long sessions: include only the first 2 turns (initial context),
    the last 3 turns (most recent), and any turns containing explicit
    architectural decisions or user approvals. Mark truncation clearly.

## Workflow

### Step 0: Run the extraction script

Use the bundled mechanical extractor to handle cwd filtering, session
discovery, TRANSCRIPT detection, and noise removal:

```bash
python3 <skill-dir>/scripts/extract_handoff.py --source <codex|pi|claude> --cwd <path>
```

Add `--json` for machine-readable output. The script handles all three
agents internally — no per-agent parsing code needed.

The script output gives you: session path, mode (transcript/direct/message),
line count, extracted turns, word/token estimates. Use this to decide
truncation strategy, then proceed with semantic interpretation.

### Step 1: Identify source

The user specifies the source agent. If ambiguous, ask.

| Source | Storage root |
|--------|-------------|
| codex  | `~/.codex/sessions/` |
| pi     | `~/.pi/agent/sessions/` |
| claude | `~/.claude/projects/` |

### Step 2: Find the latest session

**Hard constraint: filter by cwd first, timestamp second.** Always scan
candidate session files for the current working directory before picking
the newest. Otherwise you'll pick up sessions from other projects.

**Codex**: Sessions are at `sessions/YYYY/MM/DD/rollout-<ts>-<uuid>.jsonl`.
Grep recent files for the current cwd first:
```bash
grep -l "<cwd>" ~/.codex/sessions/2026/*/0[0-9]/*.jsonl 2>/dev/null | sort -r | head -1
```
If no cwd match, expand the search to older months.

**Pi**: Sessions are at `sessions/<cwd-slug>/<ts>_<uuid>.jsonl`.
The `cwd-slug` is the current working directory with `/` replaced by `--`.
Pick the most recent by filename timestamp within that directory.

**Claude Code**: Session index is at `~/.claude/sessions/<pid>.json`.
Filter by cwd in the JSON metadata, then pick highest `startedAt`.
The actual conversation is at `projects/<cwd-slug>/<sessionId>.jsonl`.

### Step 3: Extract and filter

Read the JSONL lines and filter by type:

**Codex** — has two modes. **Always scan for TRANSCRIPT first.** If the
marker `">>> TRANSCRIPT"` appears anywhere in the session, use TRANSCRIPT
mode exclusively — this is a guardian-wrapped session and direct mode
will produce garbage. Only fall back to direct mode if no TRANSCRIPT is
found. Always guard against `None` content: `if not content: continue`.

*TRANSCRIPT mode* (guardian-wrapped — check FIRST):
Codex sessions supervised by guardian/judge embed the real conversation inside
TRANSCRIPT blocks in `user_message` or `input_text` lines:

```
>>> TRANSCRIPT START
[1] user: 我想构建一个产品...
[1] assistant: 好的，让我们先...
[2] user: 再加一个功能...
>>> TRANSCRIPT END
```

Parsing strategy:
- Extract lines matching `[N] user: <text>` and `[N] assistant: <text>`.
- Ignore `[N] tool:`, `[N] system:`, `[N] guardian:`, `[N] developer:`.
- After a TRANSCRIPT START, subsequent DELTA blocks contain only new turns
  since the last approval. Deduplicate by turn number `N`, keeping the
  longest text for each `(N, role)` pair.
- Split on `[N] role:` anchors to handle multi-line messages cleanly.

*Direct mode* (fallback — only if no TRANSCRIPT found):
- Keep: `response_item` where `payload.role` is `"user"` or `"assistant"`
- Skip: `payload.role == "developer"` (system prompt / skill injection dumps)
- User content: `payload.content[].type == "input_text"` → extract `text`
- Assistant content: `payload.content[].type == "output_text"` → extract `text`
- Skip turns where every `output_text` starts with `{"outcome"` — those are
  guardian JSON responses, not real assistant replies.

*Drop list* (both modes): `function_call`, `function_call_output`,
`session_meta`, `token_count`, `turn_context`, `event_msg`,
`custom_tool_call*`, `web_search*`, `task_*`, `reasoning`, `agent_message`,
`managed`, `patch_apply_end`, `restricted`, `special`, `turn_aborted`,
`workspace-write`, `search`, `path`, `add`, `input_text`, `output_text`,
`message`, `response_item` that are raw system prompt dumps.
Also drop `response_item` with `payload.role == "developer"`.

**Pi**:
- Keep: `message` where `message.role` is `"user"` or `"assistant"`
- User content: `message.content[].type == "text"` → extract `text`
- Assistant content: `message.content[].type == "text"` → extract `text`
  (skip `type: "thinking"` blocks — they're internal reasoning, not the reply)
- Drop: `session`, `model_change`, `thinking_level_change`

**Claude Code**:
- Keep: `user` and `assistant` types
- User content: `message.content` (string)
- Assistant content: `message.content[]` — keep only `type: "text"` blocks,
  skip `type: "thinking"` blocks
- Drop: `system`, `attachment`, `custom-title`, `file-history-snapshot`,
  `last-prompt`, `queue-operation`

### Step 4: Format and inject

Format the extracted turns as a conversation transcript:

```
## Agent Handoff — [source agent] session [timestamp]

> **User**: [message text]

**Assistant**: [reply text]

> **User**: [message text]

**Assistant**: [reply text]
...
```

Present this at the beginning of your response. After the transcript,
state the next step: what the user was working on, what was just decided,
and what's pending.

### Step 5: Token budget

If the extracted transcript exceeds ~8000 words, compress in priority order:

1. **Keep always**: first 1-2 turns (initial task and constraints) and last 3
   turns (most recent decisions and pending work).
2. **Drop first**: tool-call heavy turns where the assistant had no substantive
   text response — these are execution noise, not decisions.
3. **Drop second**: repeated clarification rounds (user asks small adjustment,
   assistant acknowledges) — keep only the final adjusted requirement.
4. **Keep if possible**: assistant turns that contain architectural decisions,
   design trade-offs, or explicit user approvals — these are decision points.
5. **Drop the middle**: if still over budget after applying rules 1-4, drop
   the oldest middle turns first.
6. Mark truncation with `[... skipped N turns — tool execution and minor
   clarifications ...]`.

For sessions with 90K+ words, the compression should focus on retaining
decision density: a 3K-word summary of key decisions is more useful than
6K words of verbose assistant prose with tool calls interspersed.

## Agent-Specific Quirks

- **Codex guardian-wrapped sessions**: Most Codex sessions are supervised by
  guardian/judge agents. The real conversation is in TRANSCRIPT blocks inside
  `user_message` / `input_text` lines, NOT in `response_item` output_text.
  Auto-detect by scanning both `input_text` and `output_text` for `>>> TRANSCRIPT`
  markers — not just output_text `{"outcome"` ratio (TRANSCRIPT blocks often
  appear in input_text and would be missed). Turn numbers in DELTA blocks are
  cumulative — use `[N]` for deduplication, not line position.
- **Codex session files are per-rollout**: Multiple JSONL files in one day
  directory. Pick the most recent by filename timestamp.
- **Pi**: Sessions are keyed by working directory. If the user switched
  directories mid-session, there may be multiple session files for the
  same time period. Pick the largest file for the target cwd.
- **Claude Code**: The `startedAt` field in session JSON is Unix milliseconds.
  The `projects/<cwd-slug>/` directory only exists for sessions that had file
  editing activity. If the target session has no corresponding project JSONL,
  fall back to listing session JSON metadata only.
