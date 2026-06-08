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

从 coding agent（Claude Code / Codex / Kimi）的 conversation 中自动生成工作周报/月报，把零散会话整理成可读的工作总结。

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
python3 ~/.agents/skills/SITREP/scripts/generate_work_report.py weekly

# 生成本月月报（默认：过去30天）
python3 ~/.agents/skills/SITREP/scripts/generate_work_report.py monthly

# 指定日期范围
python3 ~/.agents/skills/SITREP/scripts/generate_work_report.py weekly --since 2026-04-01 --until 2026-04-07

# 只采集特定 agent
python3 ~/.agents/skills/SITREP/scripts/generate_work_report.py weekly --agent claude

# 只输出特定项目
python3 ~/.agents/skills/SITREP/scripts/generate_work_report.py weekly --project "test"

# 按主题过滤（主题别名在 ~/.agents/work-reports/topics.yaml 中定义）
python3 ~/.agents/skills/SITREP/scripts/generate_work_report.py weekly --topic 仿真
python3 ~/.agents/skills/SITREP/scripts/generate_work_report.py weekly --topic 工作

# 列出可用主题
python3 ~/.agents/skills/SITREP/scripts/generate_work_report.py --list-topics

# 指定输出路径
python3 ~/.agents/skills/SITREP/scripts/generate_work_report.py weekly --output ~/reports/week-12.md

# 禁用 LLM 缓存（强制重新提取 STAR）
python3 ~/.agents/skills/SITREP/scripts/generate_work_report.py weekly --no-cache

# 自动模式（无交互、日志到文件、适合 cron）
python3 ~/.agents/skills/SITREP/scripts/generate_work_report.py weekly --auto
```

### 定时自动触发（cron）

设置每周日 23:00 自动生成周报：

```bash
# 1. 确保 cron wrapper 可执行
chmod +x ~/.agents/skills/SITREP/scripts/cron_wrapper.sh

# 2. 编辑 crontab
crontab -e

# 3. 添加以下行（将 ANTHROPIC_API_KEY 替换为你的实际 key）
0 23 * * 0 ANTHROPIC_API_KEY=sk-ant-xxxxx ~/.agents/skills/SITREP/scripts/cron_wrapper.sh
```

**依赖**：
- `ANTHROPIC_API_KEY` 环境变量（可在 crontab 中直接设置，或放入 `~/.anthropic_api_key`）
- Python 3.10+ 和 `anthropic` SDK

**定时任务行为**（cron 每周日 23:00 自动执行）：
- 生成两份报告：
  1. 全量周报（所有工作）
  2. 工作周报（`--topic 工作`，仅仿真/重建相关）
- 工作周报路径带 `-work` 后缀：`weekly-YYYY-MM-DD-work.md`

**Auto 模式行为**：
- 静默执行，所有输出重定向到 `~/.agents/work-reports/.logs/auto-YYYYMMDD-HHMMSS.log`
- 自动检测 LLM 可用性：若 API key 缺失，降级为基础模式（无 STAR 提取，仅输出原始任务列表）
- 空数据周静默退出，不报错
- 生成成功后报告保存到默认路径

**主题过滤机制**：
- 主题预设文件：`~/.agents/work-reports/topics.yaml`
- 每个主题定义 `projects`（仓库名）和 `keywords`（标题关键词）两个匹配维度
- `--topic 工作` 匹配 CarlaUE5 / TadSimVehicleDynamicsDemo 仓库的所有任务

## 输出

报告默认保存到 `~/.agents/work-reports/YYYY-MM/weekly-YYYY-MM-DD.md`


## Workflow Gate Contract

SITREP report/checklist automation follows the shared workflow output contract:

```text
/home/yhr/.agents/repos/agent-skills/references/skill-output-contract.md
```

Friday checklist and Sunday final report are external handoff artifacts. The confirmed checklist is the final task source for weekly submission; sessions are evidence only unless Canon has no work tasks.

## Gotchas

- Canon task inclusion in normal work reports is strict: `report_scope: work AND weekly: true`. `weekly: true` without `report_scope: work` must not enter the checklist.
- Sunday finalization must use the confirmed checklist as the final task list. Do not leak session-only tasks into the submitted report.
- `dws report create` does not inherit template receivers. `submit_dingtalk_report.py` must carry the default receiver IDs or an explicit `REPORT_RECEIVERS_OVERRIDE`.
- Use template `周报` for title `袁浩然的周报`; template `每周工作总结` produces the wrong report title.
- In no-LLM mode, never emit placeholder text like `（通过 SITREP 自动生成）`; split completed vs in-progress tasks from rendered report status.

## Canon 输出边界

读取共享契约：`/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md`。

- `~/.agents/work-reports/` 中的周报/月报是生成报告 artifact，不是跨项目长期 source of truth。
- agent session JSONL、historical runtime recap 和 Yunxiao `state.json` 是采集源；报告中确认的长期事实应提升到 Canon project/task/pattern/incident 页面。
- 每次生成有价值的周报/月报后，创建或更新 `/media/yhr/2T/Canon/raw/update-cards/<date>-sitrep-<period>.md`，记录报告路径、时间范围、覆盖项目、关键任务和后续动作。
- Canon `artifacts/artifact-index.md` 只引用报告绝对路径或钉钉提交 URL，不复制报告。


报告采用扁平任务列表，不按项目强行分组。项目名、agent、耗时和状态作为任务元信息展示，正文尽量用自然中文说明“为什么做、做了什么、结果如何”。

报告结构：
```
# 工作周报：YYYY-MM-DD 至 YYYY-MM-DD
> 基于 N 个 agent session 自动整理，识别出 N 项有效工作。

## 1. 本周概览
本周共整理 N 项工作，完成 N 项，进行中 N 项。涉及 N 个文件的修改或检查。

## 2. 重点工作
### 2.1 任务标题
**项目**: project | **耗时**: 1h 20m | **Agent**: codex | **状态**: 已完成

本项工作围绕“任务目标”展开。

- **背景**: 这项工作出现的上下文和原因
- **目标**: 本次工作的具体目标
- **主要工作**:
  - 关键行动 1
  - 关键行动 2
  - 关键行动 3
- **结果**: 已完成的结果、当前状态或剩余问题
- **相关文件**: `path/to/file.py`
- **记录来源**: N 条用户输入，N 条 agent 回复，N 条事件
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
- **时间间隔 > 2 小时** — 长时间无活动视为任务结束
- **`/clear` 命令** — 用户主动清除上下文

合并重复：先用 title、时间和项目做低成本预合并，再在 STAR 提取后用 Situation/Task/Result 相似度和 LLM 判断合并语义相同的任务。

### 3. STAR 提取

按优先级选择数据来源：
1. **Canon task pages**（`/media/yhr/2T/Canon/tasks/*.md`）— 结构化的任务进展和决策摘要，优先作为 STAR 来源
2. **Historical runtime recap**（`~/.agent-state/conversations/*.md`）— 旧保存摘要，作为补充证据
2. **LLM 提取** — 将 conversation 文本传给 Claude，按 STAR 原则结构化

LLM prompt 要求：
- Situation: 1-2 句话说明为什么做这项工作，不暴露原始 prompt 或 session 机制
- Task: 1 句话写成工作目标，而不是聊天请求复述
- Action: 3-5 条关键行动，使用自然的工程动词，例如“梳理、实现、修正、验证、接入、清理”
- Result: 1 句话说明结果、当前状态或剩余问题
- 全部用中文输出，避免“做了一些处理”这类空泛表达

LLM 响应缓存保存在 `~/.agents/work-reports/.cache/`，重复任务秒级复用。

### 4. 渲染（Report Renderer）

生成 Markdown 报告。默认输出一个概览段落和扁平任务列表，避免把自动生成的项目路径、hash 或 session id 当成报告主结构。

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

## Canon promotion checklist

- [ ] 报告路径已作为 artifact ref 记录
- [ ] 关键任务状态已同步到对应 Canon task/project 页面，或明确说明本次只生成临时报表
- [ ] 可复用流程/风险已写入 Canon pattern/incident/update-card

## 已知限制

1. 不同表述的同一任务仍可能无法合并，尤其是文本相似度低但语义相同的长任务
2. LLM 提取质量取决于 conversation 内容完整性（被 compact 的上下文会丢失）
3. Codex 和 Kimi 的 collector 基于逆向工程，agent 更新后可能需要适配
