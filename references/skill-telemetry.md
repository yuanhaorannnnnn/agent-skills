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

## Routing schema v2

For `breach`, `acquisition`, `execute`, and `sanitize`, supply `--route` plus
closed-vocabulary routing fields. Existing calls without routing still emit v1;
old records remain readable and are counted as `unobserved`, never inferred.

- `--entry`: `skill-name` (explicit skill name/command), `natural-language`
  (ordinary user request), `caller` (another workflow), or `unknown`.
- `--trigger`: `explicit` when the user names the skill, `implicit` for automatic
  selection from natural language, `workflow` for a caller. Entry form and trigger
  category are metadata, not the original request.
- `--route`: actual branch entered, including a branch that failed.
- `--expected-route`: only an unambiguous user/caller requirement. Leave unset
  when unclear or when the route is an agent's automatic choice.
- `--decision KEY=VALUE`: selection metadata from the table below.
- `--step NAME=STATE`: observed execution/check result. States:
  `pass|blocked|skipped|error|pending`. Missing means unobserved, not skipped.
  A selected but unexecuted step is `pending`; `pass` requires completion.
- `route_match`: computed comparison, `null` without explicit expectation.
  A mismatch does not rewrite the workflow outcome; it is a separate diagnostic.

| Skill | Allowed routes | Decision vocabulary | Step names |
|---|---|---|---|
| breach | general-page, discussion-digest, native-handoff, inline-answer, unresolved | content-profile: default/eli5; prose: author/faithful; style: project-design/selected-design/awesome-design/digest-template/none; charts: lieflat/native/omit/unavailable; hairline: embed/static/omit/unavailable | paperwork, layout, style, render, charts, hairline, visual-check |
| acquisition | article, wechat-article, wechat-album, video, pdf, clippings, local-markdown, chart-handoff, deduplicated, unresolved | identity: new/complete/raw-only/incomplete/changed/weak; delivery: raw-query/raw-only/handoff/reuse; fetch: direct/jina/wechat-cli/youtube/x-download/local/none | identity, archive, paperwork, query, index-log, catalog, handoff |
| execute | direct, delegate, unresolved | requested: auto/direct/delegate; persistence: local/task/goal/plan | implementation, delegation, validation, review, execution-gate |
| sanitize | closeout, report, both, unresolved | publish: none/commit/push (highest completed action) | report, report-gate, review, commit, push, canon |

Unknown skills, routes, keys, values, and duplicate keys are rejected before
append. Do not put free-text reasons, subject names, URLs, layout names, model
names, or user text into routing fields. Exact sources stay in artifact/gate
references and artifact provenance, not in an unrestricted metadata map.

Example invocation **after actual work** (replace states and refs with observed
results; never run this example merely to create a success event):

```bash
python3 <skills-root>/.scripts/skill_telemetry.py \
  --skill breach --runtime codex --trigger implicit \
  --entry natural-language --outcome pass \
  --route discussion-digest --expected-route discussion-digest \
  --decision content-profile=default --decision prose=author \
  --decision style=digest-template --decision charts=omit --decision hairline=omit \
  --step paperwork=pass --step layout=skipped --step style=pass \
  --step render=pass --step charts=skipped --step hairline=skipped \
  --step visual-check=pending --artifact /absolute/digest.html
```

Record the final local verdict once, including failures/skips, using the state
retained from entry. Do not add a second v1 outcome event. Nested skills keep
separate events. If a task is interrupted before emission, no record is guaranteed;
this recorder is not a runtime hook and cannot observe an unloaded skill or an
agent that ignores the instructions. Step results are agent-reported observations,
not independent attestation. Check linked gate/artifact evidence for stronger proof.

## Read-only query

```bash
python3 <skills-root>/.scripts/skill_telemetry.py --report --skill breach
python3 <skills-root>/.scripts/skill_telemetry.py --report
```

Returns counts for outcomes, routes, entry forms, decisions, executed step states,
and explicit expectation mismatches. `unknown_expectations` includes v1 events
and events with no explicit expected route; they never count as matches.
`invalid_lines` counts malformed records (including a partially written final
line), which are skipped. A missing log returns empty counts without creating it.
The report prints only validated metadata, never arbitrary legacy fields or refs.
Usage counts cover emitted events only, not total skill usage across all sessions.
