# Cron Ops — Scheduling, Fallback, Troubleshooting

## Friday Checklist

Friday is the checklist generation day — NOT the final submission. The Friday checklist is the confirmed task source for Sunday's final report.

```bash
python3 ~/.agents/skills/SITREP/scripts/generate_work_report.py weekly --auto --checklist
```

Output: confirmed checklist to `~/.agents/work-reports/checklist-YYYY-MM-DD.md`.

## Sunday Finalize

Sunday finalization uses the confirmed checklist (most recent Friday or Saturday checklist), not a fresh data scan. The checklist is the final task list source — do NOT leak session-only tasks into the submitted report.

```bash
python3 ~/.agents/skills/SITREP/scripts/generate_work_report.py weekly --auto --finalize --from-checklist <checklist-path>
```

Generates two reports:
1. Full weekly (`weekly-YYYY-MM-DD.md`)
2. Work weekly (`weekly-YYYY-MM-DD-work.md`) — `--topic 工作` filtered

## Fallback Rules

If no Friday/Saturday checklist exists:
- Fall back to the most recent checklist from the current week
- If no checklist at all: generate one from Canon + session data, mark as `[auto-generated, please review]`
- Never submit a report without at least one reviewed checklist as source

## Crontab

```bash
# Friday 18:00 — generate checklist
0 18 * * 5 ANTHROPIC_API_KEY=sk-ant-xxxxx ~/.agents/skills/SITREP/scripts/cron_wrapper.sh --checklist

# Sunday 23:00 — finalize and submit
0 23 * * 0 ANTHROPIC_API_KEY=sk-ant-xxxxx ~/.agents/skills/SITREP/scripts/cron_wrapper.sh --finalize
```

## Environment

- `ANTHROPIC_API_KEY`: required for LLM STAR extraction. Set in crontab or `~/.anthropic_api_key`.
- Python 3.10+
- Working directory: any (scripts use absolute paths)

## Manual Rerun

If cron fails or data is stale:
```bash
# Re-run checklist
python3 ~/.agents/skills/SITREP/scripts/generate_work_report.py weekly --since ... --until ... --auto --checklist

# Re-run final report
python3 ~/.agents/skills/SITREP/scripts/generate_work_report.py weekly --finalize --from-checklist <checklist>
```

## Log Troubleshooting

Auto mode logs: `~/.agents/work-reports/.logs/auto-YYYYMMDD-HHMMSS.log`

Common failures:
- Missing API key → auto-degrade to no-LLM mode (basic task list, no STAR)
- Empty data week → silent exit, no error
- Collector parsing failure → skip that agent, continue with others, log warning
- DingTalk submission failure → retry once, log error with details
