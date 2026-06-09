# DingTalk Report — Template, Receivers, Submit

## Report Template

Use template `周报` for title `袁浩然的周报`. Do NOT use template `每周工作总结` — wrong title.

## Receiver Configuration

`submit_dingtalk_report.py` must carry default receiver IDs or an explicit `REPORT_RECEIVERS_OVERRIDE` env var. `dws report create` does NOT inherit template receivers.

Default receivers (from config):
```
REPORT_RECEIVERS_OVERRIDE="<comma-separated userIds>"
```

## Markdown → Log Field Conversion

The DingTalk report log uses structured fields. When submitting:
- Report title → template `周报` → title field `袁浩然的周报`
- Report body markdown → converted to DingTalk rich text format
- Receivers → resolved to userIds from config or env override

## Submit via Script

```bash
python3 ~/.agents/skills/SITREP/scripts/submit_dingtalk_report.py \
  --report <path-to-weekly.md>
```

Or use dws MCP directly:
```
dws report create --template "周报" --title "袁浩然的周报" --receivers "<userIds>"
```

## No-LLM Mode Notes

In no-LLM mode: never emit placeholder text like `（通过 SITREP 自动生成）`. Split completed vs in-progress tasks from rendered report status — use the Canon task phase field to determine completion.
