# Skill Telemetry Contract

Record one local outcome event when a skill materially passes, blocks, skips, or
errors. Telemetry measures workflow use and gate outcomes; it never stores the
conversation.

```bash
python3 <skills-root>/.scripts/skill_telemetry.py \
  --skill passdown \
  --runtime codex \
  --trigger explicit \
  --outcome pass \
  --duration-ms 1250 \
  --artifact /absolute/artifact/path \
  --gate /absolute/gate/path
```

Default destination:

```text
~/.agents/skill-telemetry/events.jsonl
```

Override only for tests or controlled exports with `SKILL_TELEMETRY_PATH` or
`--path`.

## Schema v1

```json
{
  "schema_version": 1,
  "timestamp": "UTC ISO-8601",
  "skill": "manifest skill name",
  "runtime": "codex|claude|pi|kimi|other",
  "trigger": "explicit|implicit|workflow",
  "outcome": "pass|blocked|skipped|error",
  "duration_ms": 1250,
  "artifacts": ["absolute path or URL"],
  "gate": "absolute path or null"
}
```

## Privacy And Failure Rules

- Never record prompts, responses, transcript text, tool arguments, source
  content, tokens, credentials, environment values, or arbitrary exception text.
- Emit at most once per skill invocation. Nested skills emit their own event.
- Telemetry failure is a warning, not a reason to change the skill outcome.
- JSONL is local, append-only, mode `0600`; no daemon, database, or network.
