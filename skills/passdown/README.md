# passdown

`passdown` transfers useful context from an earlier coding-agent session into
the current one. It discovers Codex, Pi, Claude Code, and DSH sessions, filters
for the requested topic, removes duplicate turns, and returns a bounded,
readable handoff. It transfers conversation context—not workspace ownership or
implementation files.

## Quick start

From the current workspace:

```bash
python3 /home/yhr/.agents/repos/agent-skills/skills/passdown/scripts/extract_handoff.py \
  --focus "your task or topic" --json
```

Useful variations:

```bash
# Search another workspace and identify one runtime explicitly
python3 /home/yhr/.agents/repos/agent-skills/skills/passdown/scripts/extract_handoff.py \
  --former codex --dir /absolute/source/workspace --focus "your task" --json

# Select one known session, or read one session file directly
python3 /home/yhr/.agents/repos/agent-skills/skills/passdown/scripts/extract_handoff.py \
  --session SESSION_UUID --json
python3 /home/yhr/.agents/repos/agent-skills/skills/passdown/scripts/extract_handoff.py \
  --file /absolute/session.jsonl --former claude --json
```

`--focus` searches all matching candidates, then the extractor ranks recent and
relevant turns and deduplicates overlapping content. Use `--max-tokens` to set
a stricter output budget. For focused retrieval, `--retriever auto` may use the
optional local zvec index and otherwise falls back to keyword/mtime retrieval;
`--retriever zvec` is strict and fails when the index has no candidate.

## Relationship to Canon

Passdown is the hot-context layer. Before using it, resume from the resolved
Canon task page when one exists; use the page's stable summary and incomplete
next step to choose the focus. Keep durable project state, decisions, task
state, and artifact references in Canon. A handoff may identify a Canon page or
artifact, but it does not promote or copy that material automatically. See the
[Canon task resolution](../../references/canon-task-resolution.md) and [Canon
output contract](../../references/canon-output-contract.md).

## Generic example

```text
New session: "Continue the camera calibration fix."
1. Resolve the relevant Canon task and read its current next step.
2. Run passdown with --focus "camera calibration" in the source workspace.
3. Check the returned source session, decisions, pending work, and artifact map.
4. Inspect referenced artifacts in their source workspace before acting.
```

For a cross-directory handoff, artifacts remain owned by the source workspace;
report absolute paths rather than silently copying plans, logs, reports, or
build outputs.

## Cross-model handoff (Review + Passdown)

When a GPT model (Codex Terra/Sol/Luna, ChatGPT) takes over a session from
DeepSeek or Gemini (DSH, `deepseek-v4-flash`, Gemini CLI), `passdown` enters
`review+passdown`. The incoming GPT agent performs a read-only evidence audit
on the pending handoff content (validating real on-disk artifacts, checking
metric sanity, and separating verified facts from static code conjectures)
before finalizing the handoff.

## Recovery boundaries

Passdown can recover filtered conversation turns and visible references to
decisions, pending work, and artifacts from readable session logs. It cannot
recover missing or corrupted session data, unrecorded work, hidden tool output,
workspace ownership, or a guaranteed final implementation state. Extraction is
read-only on session storage. Archival is a separate, optional lifecycle action
and requires the conditions described in [`SKILL.md`](./SKILL.md).

For implementation details and supported session formats, see [`SKILL.md`](./SKILL.md).
The extractor's regression coverage is in [`tests/test_extract_handoff.py`](./tests/test_extract_handoff.py).
