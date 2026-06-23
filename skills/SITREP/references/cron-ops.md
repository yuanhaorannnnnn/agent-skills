# Cron Ops — Scheduling, Fallback, Troubleshooting

## Current Policy

Agent does not write or submit the final weekly report. The user writes it manually.
Cron only sends a DingTalk document containing raw weekly reference materials.

```bash
30 17 * * 5 /home/yhr/.agents/skills/SITREP/scripts/weekly_materials.sh >> /home/yhr/.agents/work-reports/logs/weekly-materials.log 2>&1
```

Output:

- DingTalk doc title: `周报参考素材 · M/D - M/D`
- Local Markdown: `~/.agents/work-reports/weekly-materials-YYYY-MM-DD.md`
- Metadata: `~/.agents/work-reports/.materials/materials-YYYY-MM-DD.json`

This doc is not a checklist and not the final weekly report.

## Deprecated Friday Checklist

```bash
python3 ~/.agents/skills/SITREP/scripts/generate_work_report.py weekly --auto --checklist
```

Deprecated. Do not send the weekly checklist unless the user explicitly asks for it.

## Deprecated Sunday Finalize

```bash
python3 ~/.agents/skills/SITREP/scripts/generate_work_report.py weekly --auto --finalize --from-checklist <checklist-path>
```

Deprecated. Do not auto-submit DingTalk weekly reports. The user writes the final report manually.

## Crontab

```bash
# Friday 17:30 — generate raw weekly materials DingTalk doc
30 17 * * 5 /home/yhr/.agents/skills/SITREP/scripts/weekly_materials.sh >> /home/yhr/.agents/work-reports/logs/weekly-materials.log 2>&1

# Deprecated: Friday checklist + Sunday finalize are disabled.
```

## Environment

- Python 3.10+
- `dws` CLI authenticated for DingTalk doc creation and self-message sending
- Working directory: any (scripts use absolute paths)

## Manual Rerun

If cron fails or data is stale:

```bash
/home/yhr/.agents/skills/SITREP/scripts/weekly_materials.sh --since YYYY-MM-DD --until YYYY-MM-DD
```

Dry-run without DingTalk operations:

```bash
/home/yhr/.agents/skills/SITREP/scripts/weekly_materials.sh --dry-run
```

## Log Troubleshooting

Cron log: `~/.agents/work-reports/logs/weekly-materials.log`

Common failures:

- DingTalk auth expired → run `dws auth status --format json`, then rerun
- Empty data week → document contains empty source sections
- Collector parsing failure → skip that agent, continue with others, log warning
- DingTalk document/message failure → local Markdown remains saved
