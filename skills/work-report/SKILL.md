---
name: work-report
description: |
  Generate weekly or monthly work reports from coding agent conversations (Claude Code, Codex, Kimi).
  Use this skill whenever the user mentions work reports, weekly summaries, monthly summaries,
  work logs, 周报, 月报, 工作总结, or wants to track what they've accomplished through coding agents.
  Also trigger when the user asks to summarize their recent work, review progress, or generate
  a work recap from agent sessions.
---

# Work Report

从 coding agent（Claude Code / Codex / Kimi）的 conversation 中自动生成工作周报/月报，按 STAR 原则结构化输出。

## 为什么需要这个 skill

传统工作软件（钉钉、飞书）无法记录 coding agent 中的工作内容。但 agent conversation 包含了完整的任务上下文、技术决策和代码变更——这正是工作记录的最佳数据来源。这个 skill 自动采集、结构化并生成报告，替代手动整理。

## 触发方式

用户可能用以下方式表达需求：
- `/work-report weekly` / `周报`
- `/work-report monthly` / `月报`
- "总结下这周的工作" / "生成工作周报"
- "work report" / "weekly summary" / "monthly report"

## 用法

```bash
# 生成本周周报（默认：过去7天）
python3 ~/.agents/skills/.scripts/generate_work_report.py weekly

# 生成本月月报（默认：过去30天）
python3 ~/.agents/skills/.scripts/generate_work_report.py monthly

# 指定日期范围
python3 ~/.agents/skills/.scripts/generate_work_report.py weekly --since 2026-04-01 --until 2026-04-07

# 只采集特定 agent
python3 ~/.agents/skills/.scripts/generate_work_report.py weekly --agent claude

# 只输出特定项目
python3 ~/.agents/skills/.scripts/generate_work_report.py weekly --project "test"

# 指定输出路径
python3 ~/.agents/skills/.scripts/generate_work_report.py weekly --output ~/reports/week-12.md

# 禁用 LLM 缓存（强制重新提取 STAR）
python3 ~/.agents/skills/.scripts/generate_work_report.py weekly --no-cache

# 自动模式（无交互、日志到文件、适合 cron）
python3 ~/.agents/skills/.scripts/generate_work_report.py weekly --auto
```

### 定时自动触发（cron）

设置每周日 23:00 自动生成周报：

```bash
# 1. 确保 cron wrapper 可执行
chmod +x ~/.agents/skills/.scripts/cron_wrapper.sh

# 2. 编辑 crontab
crontab -e

# 3. 添加以下行（将 ANTHROPIC_API_KEY 替换为你的实际 key）
0 23 * * 0 ANTHROPIC_API_KEY=sk-ant-xxxxx ~/.agents/skills/.scripts/cron_wrapper.sh
```

**依赖**：
- `ANTHROPIC_API_KEY` 环境变量（可在 crontab 中直接设置，或放入 `~/.anthropic_api_key`）
- Python 3.10+ 和 `anthropic` SDK

**Auto 模式行为**：
- 静默执行，所有输出重定向到 `~/.agents/work-reports/.logs/auto-YYYYMMDD-HHMMSS.log`
- 自动检测 LLM 可用性：若 API key 缺失，降级为基础模式（无 STAR 提取，仅输出原始任务列表）
- 空数据周静默退出，不报错
- 生成成功后报告保存到默认路径

## 输出

报告默认保存到 `~/.agents/work-reports/YYYY-MM/weekly-YYYY-MM-DD.md`

报告结构：
```
# Weekly Work Report - YYYY-MM-DD to YYYY-MM-DD
## Summary（统计概览：任务数、完成数、进行中数、修改文件数）
## By Project（按项目分组）
### Project A
#### Task 1
- **Situation**: 背景/上下文
- **Task**: 目标
- **Action**: 关键行动步骤（3-5 条）
- **Result**: 结果
- **Stats**: N prompts, N responses, N events
## Daily Breakdown（按日汇总）
## In Progress / Pending（进行中任务）
## Completed This Week（已完成任务）
## Files Modified（文件列表）
```

## 工作原理

### 1. 采集（Collectors）

读取各 agent 的 conversation JSONL，提取关键事件：

| Agent | 数据源 |
|-------|--------|
| Claude Code | `~/.claude/projects/<project>/<session>.jsonl` |
| Codex | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` |
| Kimi | `~/.kimi/sessions/<hash>/<subsession>/wire.jsonl` |

提取内容：user prompt、assistant response、file change、tool call、system error。
自动过滤 meta 命令（`/clear`, `/login`）和系统噪音。

### 2. 聚类（Task Clustering）

将连续的事件流切分为独立的任务单元。切分信号：
- **不同 session_id** — 新开 session 通常是新任务
- **时间间隔 > 30 分钟** — 长时间无活动视为任务结束
- **`/clear` 命令** — 用户主动清除上下文

合并重复：归一化 title 后，相似度 ≥ 85% 且同一项目 + 24 小时内的任务合并。

### 3. STAR 提取

按优先级选择数据来源：
1. **Save-conversation 摘要**（`~/.agent-state/conversations/*.md`）— 人工编辑过的最高质量摘要
2. **LLM 提取** — 将 conversation 文本传给 Claude，按 STAR 原则结构化

LLM prompt 要求：
- Situation: 1-2 句话描述背景
- Task: 1 句话描述目标
- Action: 3-5 条关键行动（文件修改、技术决策、命令执行）
- Result: 结果或当前状态
- 全部用中文输出

LLM 响应缓存保存在 `~/.agents/work-reports/.cache/`，重复任务秒级复用。

### 4. 渲染（Report Renderer）

生成 Markdown 报告，按项目分组，每日汇总。

## 关键文件

```
skills/work-report/
├── SKILL.md                           # 本文件
└── scripts/
    ├── generate_work_report.py        # 主 CLI 入口
    ├── cron_wrapper.sh                # cron 定时触发 wrapper
    ├── normalizer.py                  # 统一数据模型（Event, Session）
    ├── common_wr.py                   # 共享工具（时间解析、噪音过滤）
    ├── task_clustering.py             # 任务聚类 + 去重
    ├── star_builder.py                # LLM STAR 提取 + 缓存
    ├── report_renderer.py             # Markdown 渲染
    └── collectors/
        ├── claude_collector.py        # Claude Code JSONL 解析
        ├── codex_collector.py         # Codex session 解析
        └── kimi_collector.py          # Kimi wire.jsonl 解析
```

## 依赖

- Python 3.10+
- `anthropic` SDK（`pip install anthropic`）
- `ANTHROPIC_API_KEY` 环境变量

## 性能

- 数据采集：本地文件读取，秒级完成
- STAR 提取：首次需 LLM API 调用（~1-2s/任务），缓存后秒级
- 100 个任务的全流程约 2-3 分钟（含 LLM）

## 已知限制

1. 重复任务合并依赖 title 相似度，不同表述的同一任务可能无法合并
2. LLM 提取质量取决于 conversation 内容完整性（被 compact 的上下文会丢失）
3. Codex 和 Kimi 的 collector 基于逆向工程，agent 更新后可能需要适配
