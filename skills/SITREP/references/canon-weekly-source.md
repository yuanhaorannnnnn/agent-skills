# Canon Weekly Source — Task Filtering & Dedup Rules

## Canon Task Inclusion

Canon task pages (`/media/yhr/2T/Canon/tasks/*.md`) are the primary source for weekly reports. Inclusion is strict:

**Must have both:**
- `report_scope: work` — the task is a work item (not infra/personal/ignore)
- `weekly: true` — the task is active this week and should appear in reports

**Excluded:**
- `weekly: true` without `report_scope: work` — must NOT enter the checklist
- `report_scope: ignore` or `personal` — never included
- `report_scope: infra` — only included if explicitly requested

## report_scope / weekly Relationship

| report_scope | weekly | Included? |
|-------------|--------|-----------|
| `work` | `true` | ✅ |
| `work` | `false` / unset | ❌ |
| `infra` | `true` | ⚠️ only if explicitly requested |
| `personal` | any | ❌ |
| `ignore` | any | ❌ |
| unset | any | ❌ |

## Session JSONL & Historical Recap

Session data (`~/.claude/projects/`, `~/.codex/sessions/`, `~/.kimi/sessions/`) is evidence only — not the primary task source. Use it to:

1. Fill in details for Canon tasks (what was actually done, files changed, time spent)
2. Discover ad-hoc work that has no Canon task page (one-off fixes, quick investigations)
3. Verify that Canon task claims match actual session activity

**Rule**: Canon task page is truth. Session evidence supports, does not replace. If a session task has no matching Canon page, include it but mark `[no Canon task]`.

## Dedup & Merge Rules

1. **Same Canon task ID** → merge all sessions into one report entry
2. **Same file changes across sessions** → merge if timestamps within 24h
3. **Text similarity > 0.7 on title + first 100 chars** → candidate merge, use LLM to decide
4. **Different agents, same task** → merge, track agent source as metadata

## Filtering

- Meta commands (`/clear`, `/login`, `/config`) always excluded
- System noise (compaction notices, idle markers) excluded
- Tasks with < 2 agent turns excluded (too thin)
- Tasks older than report period excluded by collector timestamp filter
