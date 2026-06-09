---
name: SITREP
description: |
  Generate weekly or monthly work reports from coding agent conversations (Claude Code, Codex, Kimi).
  Use this skill whenever the user mentions work reports, weekly summaries, monthly summaries,
  work logs, 周报, 月报, 工作总结, or wants to track what they've accomplished through coding agents.
  Also trigger when the user asks to summarize their recent work, review progress, or generate
  a work recap from agent sessions.
---

# Work Report

从 coding agent conversation 中自动生成工作周报/月报。数据采集→任务聚类→STAR 提取→渲染→提交。

## 用法

```bash
# Weekly (default: past 7 days)
python3 ~/.agents/skills/SITREP/scripts/generate_work_report.py weekly

# Monthly (default: past 30 days)
python3 ~/.agents/skills/SITREP/scripts/generate_work_report.py monthly

# With options
python3 ~/.agents/skills/SITREP/scripts/generate_work_report.py weekly --agent claude --topic 工作 --auto
```

## 数据源优先级

1. **Canon task pages** (`/media/yhr/2T/Canon/tasks/*.md`) — primary source, structured task state
2. **Historical runtime recap** (`~/.agent-state/conversations/*.md`) — supplementary evidence
3. **Session JSONL** — Claude Code/Codex/Kimi conversation logs — evidence only, not task definition

Canon task inclusion 规则见 `references/canon-weekly-source.md`。

## 工作流

```
Collect → Cluster → STAR Extract → Render → Submit
```

### 1. Collect

读取各 agent JSONL，按时间范围和 agent 过滤。自动排除 meta 命令和系统噪音。

| Agent | Source |
|-------|--------|
| Claude Code | `~/.claude/projects/<project>/<session>.jsonl` |
| Codex | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` |
| Kimi | `~/.kimi/sessions/<hash>/<subsession>/wire.jsonl` |

### 2. Cluster

将事件流切分为独立任务。切分信号：不同 session_id、间隔 >2h、`/clear`。合并信号：相同 Canon task ID、相同文件变更（24h 内）、标题+前 100 字相似度 >0.7 + LLM 判断。

### 3. STAR Extract

LLM 将 conversation 转为结构化 STAR（Situation/Task/Action/Result），全部中文输出。LLM 响应缓存：`~/.agents/work-reports/.cache/`。

No-LLM mode：不生成占位文字，从 Canon task phase 判断完成/进行中。

### 4. Render

Markdown 报告。扁平任务列表，项目名/agent/耗时/状态作为元信息。输出路径：`~/.agents/work-reports/YYYY-MM/weekly-YYYY-MM-DD.md`。

### 5. Submit & Gate

周五 checklist 生成后跑：
```bash
python3 ~/.claude/skills/SITREP/scripts/report_gate.py --mode checklist <checklist.md>
```

周日 final report 生成后跑：
```bash
python3 ~/.claude/skills/SITREP/scripts/report_gate.py --mode report <report.md> --checklist <checklist.md>
```

blocked → 缺文件或空。Checklist 模式检查文件存在 + 非空 + Canon 来源。Report 模式检查文件存在 + 基于 checklist（非 fresh scan）+ 非空。

提交流程详见 `references/dingtalk-report.md` 和 `references/cron-ops.md`。

## 输出类型

| Type | Trigger | Description |
|------|---------|-------------|
| **Checklist** | Friday auto | Confirmed task list for review |
| **Weekly** | Sunday finalize | Full weekly report + work-filtered version |
| **Monthly** | End of month | Aggregated monthly summary |

## 关键文件

```
skills/SITREP/
├── SKILL.md
├── references/
│   ├── canon-weekly-source.md    # Canon task filtering, dedup, merge rules
│   ├── dingtalk-report.md        # DingTalk template, receivers, submit notes
│   └── cron-ops.md               # Friday/Sunday schedule, fallback, troubleshooting
└── scripts/
    ├── generate_work_report.py    # Main CLI entry
    ├── cron_wrapper.sh            # Cron trigger wrapper
    ├── normalizer.py              # Unified data model
    ├── task_clustering.py         # Clustering + dedup
    ├── star_builder.py            # LLM STAR + cache
    ├── report_renderer.py         # Markdown renderer
    └── collectors/                # Claude/Codex/Kimi JSONL parsers
```

## Gotchas

- Canon task inclusion: `report_scope: work AND weekly: true`. `weekly: true` without `report_scope: work` → excluded.
- Sunday finalize uses confirmed checklist, not fresh data scan.
- `dws report create` does not inherit template receivers — `submit_dingtalk_report.py` must carry defaults.
- Template `周报` for title `袁浩然的周报`; NOT `每周工作总结`.
- No-LLM mode: never emit placeholder text; split completed/in-progress from report status.

## 资源

- `references/canon-weekly-source.md` — Canon task 筛选、session 证据地位、去重合并规则
- `references/dingtalk-report.md` — 钉钉模板、接收人、Markdown→日志字段转换
- `references/cron-ops.md` — 周五 checklist/周日 finalize、crontab、手动补跑、日志排错
