# Work-Report Skill Design Document

**Date**: 2026-04-27
**Module**: `agent-skills/skills/work-report`
**Author**: Claude Code / Infra Conversation

---

## Executive Summary

`work-report` 是一个从 coding agent（Claude Code、Codex、Kimi）的 conversation JSONL 日志中自动生成结构化工作周报/月报的 skill。系统采用五阶段 pipeline 架构，核心创新在于**两阶段去重策略**（rule-based 预过滤 + LLM 语义确认），将去重的 LLM 调用复杂度从 O(N^2) 降低到 O(candidates)。所有任务按 STAR 原则（Situation-Task-Action-Result）结构化输出，支持交互式和定时自动（cron）两种触发模式。

---

## Architecture / Flow

### Overall Pipeline

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Collectors    │────>│   Normalizer    │────>│ Task Clustering │
│ (3 Agent Types) │     │  (Event/Session)│     │ (Split + Merge) │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                              ┌──────────────────────────┘
                              ▼
                    ┌─────────────────┐
                    │  Two-Stage      │
                    │  Deduplication  │
                    │  (Rule + LLM)   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐     ┌─────────────────┐
                    │   STAR Builder  │────>│ Report Renderer │
                    │  (LLM Extract)  │     │  (Markdown)     │
                    └─────────────────┘     └─────────────────┘
```

### Data Flow Detail

```
Claude Code            Codex                Kimi
   │                     │                   │
   ▼                     ▼                   ▼
┌──────────┐      ┌──────────┐       ┌──────────┐
│ ~/.claude│      │ ~/.codex │       │ ~/.kimi  │
│/projects │      │/sessions │       │/sessions │
│/*.jsonl  │      │/YYYY/... │       │/*/wire   │
└────┬─────┘      └────┬─────┘       │ .jsonl  │
     │                 │             └────┬────┘
     └────────┬────────┴─────────────────┘
              ▼
     ┌─────────────────┐
     │  Collector      │
     │  (Agent-specific│
     │   JSONL parse)  │
     └────────┬────────┘
              │ list[Session]
              ▼
     ┌─────────────────┐
     │  Task Clustering│
     │  1. Split by    │
     │     /clear, gap │
     │  2. Merge by    │
     │     similarity  │
     └────────┬────────┘
              │ list[Task]
              ▼
     ┌─────────────────┐
     │  STAR Builder   │
     │  (LLM Extract   │
     │   + Cache)      │
     └────────┬────────┘
              │ list[Task] w/ STAR
              ▼
     ┌─────────────────┐
     │  Two-Stage      │
     │  Deduplication  │
     │  (Rule-based    │
     │   + LLM conf.)  │
     └────────┬────────┘
              │ list[Task] merged
              ▼
     ┌─────────────────┐
     │  Report Renderer│
     │  (Markdown      │
     │   Output)       │
     └────────┬────────┘
              ▼
     ~/.agents/work-reports/
     YYYY-MM/weekly-YYYY-MM-DD.md
```

### Two-Stage Deduplication Sub-Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     Stage 1: Rule-Based                      │
│  Compute _star_similarity() for all candidate pairs          │
│  Situation weight=0.5, Task=0.3, Result=0.2                 │
│  Filter: sim >= 0.05 AND within 7 days                      │
│  Output: candidate pairs (O(N^2) -> ~O(N) in practice)      │
└──────────────────────────┬──────────────────────────────────┘
                           │ candidate pairs
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     Stage 2: LLM Confirm                     │
│  For each candidate:                                         │
│    call Claude Haiku 4.5 with STAR comparison prompt        │
│    max_tokens=10, temperature=0                             │
│    answer: "yes" or "no"                                    │
│  LLM judgment OVERRIDES all other rules                     │
└──────────────────────────┬──────────────────────────────────┘
                           │ confirmed merge pairs
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     Stage 3: Union-Find                      │
│  Build merge groups via union-find (disjoint sets)          │
│  Merge each group: combine sessions, events, files          │
│  Preserve: best title, all unique actions                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Logic

### 1. Task Segmentation (Session -> Task Segments)

一个 Session 可能被切分为多个 Task Segment，切分信号按优先级排序：

| Signal | Threshold | Rationale |
|--------|-----------|-----------|
| `/clear` command | immediate | User explicitly resets context |
| Time gap | > 120 min | User took a long break |
| Working dir change | any change | Switched to different project |
| Git branch change | any change | Context switch to different feature |

实现位于 `task_clustering.py:_split_session_into_segments()`。

### 2. Title-Driven Pre-Merge (Segments -> Tasks)

切分后的 segments 先经过一轮基于 title 相似度的合并：

```python
# _should_merge_tasks() logic
if same_project AND within_24h:
    if title_similarity >= 0.6:      → merge
    if content_similarity >= 0.25:   → merge
```

Title similarity 使用归一化后比较（去空格/标点，小写），支持：
- 精确匹配
- 子串匹配（最小长度 10）
- 前缀匹配（80% 相同前缀）

Content similarity 基于 assistant response 的指纹比较（Jaccard-like score），使用 assistant response 而非 user prompt，因为用户输入可能在同一对话中变化很大（"continue"、"ok"），但 agent 的回复承载实际工作内容。

### 3. STAR Similarity Computation

用于第二阶段去重的核心相似度算法，基于已提取的 STAR 字段：

```
score = sit_score * 0.5 + task_score * 0.3 + result_score * 0.2

sit_score:   Situation 的 4-gram Jaccard（或精确/子串匹配）
task_score:  Task description 的 3-gram Jaccard
result_score: Result 的 4-gram Jaccard
```

设计原则：**Situation 权重最高（0.5）**，因为两个描述同一工作的任务最可能共享相似的背景上下文。

### 4. LLM Merge Judgment

当 rule-based similarity >= 0.05 时，触发 LLM 二次确认：

- **Model**: Claude Haiku 4.5（fast, cheap）
- **Parameters**: max_tokens=10, temperature=0
- **Prompt**: 对比两个任务的 STAR 内容，回答 "yes" 或 "no"
- **规则**: LLM 说 "yes" 则合并，无视项目、agent、状态、/clear 边界等一切其他规则

这是整个系统最关键的设计决策：**LLM 的判断具有最高优先级**，因为语义理解是规则算法无法替代的。

### 5. Duration Calculation

任务时长使用**活跃时间**而非会话起止时间：

```
active_time = sum(gaps <= 2h between consecutive events)
```

大于 2 小时的时间间隔视为用户离开（休息/下班），不计入工作时长。

### 6. STAR Extraction Priority

每个任务的 STAR 提取按以下优先级选择数据源：

1. **Historical runtime recap**（`~/.agent-state/conversations/*.md`）— 旧保存摘要，作为补充证据
2. **LLM 提取** — 将 conversation 文本传给 Claude，按 STAR 原则结构化

LLM 提取结果通过 SHA256 缓存到 `~/.agents/work-reports/.cache/`，重复任务秒级复用。

---

## Data Sources

| Agent | Data Path | Format | Key Fields |
|-------|-----------|--------|------------|
| Claude Code | `~/.claude/projects/<project>/<session>.jsonl` | JSONL | type, timestamp, message.content, cwd, gitBranch |
| Codex | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` | JSONL | payload.type, timestamp, payload.message |
| Kimi | `~/.kimi/sessions/<hash>/<subsession>/wire.jsonl` | JSONL | message.type, message.payload |
| Kimi (fallback) | `~/.kimi/sessions/<hash>/<subsession>/context.jsonl` | JSONL | role, content |

### Metadata Sources

| Source | File | Purpose |
|--------|------|---------|
| Claude session index | `~/.claude/projects/<project>/sessions-index.json` | Title, first prompt, creation time |
| Claude session metadata | `~/.claude/sessions/<pid>.json` | Session name, cwd |
| Codex session index | `~/.codex/session_index.jsonl` | Thread name, updated_at |
| Kimi state | `~/.kimi/sessions/<hash>/<subsession>/state.json` | Custom title |
| Conversation summary | `.agent-state/conversations/<name>.md` | STAR extraction priority 1 |

---

## Code Navigation

| File | Class / Function | Responsibility |
|------|------------------|----------------|
| `generate_work_report.py` | `main()`, `cmd_weekly()`, `cmd_monthly()` | CLI entry, argument parsing, orchestration, auto mode |
| `normalizer.py` | `Event`, `Session` | Unified data model across all agents |
| `common_wr.py` | `parse_iso_timestamp()`, `parse_unix_timestamp()`, `is_noise()`, `get_week_range()` | Shared utilities, time parsing, noise filtering |
| `collectors/claude_collector.py` | `collect_claude_sessions()`, `_parse_claude_jsonl()` | Claude Code JSONL parsing |
| `collectors/codex_collector.py` | `collect_codex_sessions()`, `_parse_codex_jsonl()` | Codex session JSONL parsing |
| `collectors/kimi_collector.py` | `collect_kimi_sessions()`, `_parse_kimi_subsession()`, `_parse_wire_jsonl()` | Kimi wire/context JSONL parsing |
| `task_clustering.py` | `cluster_sessions()`, `_split_session_into_segments()`, `_merge_similar_tasks()` | Task segmentation and title-driven pre-merge |
| `task_clustering.py` | `merge_by_star_similarity()`, `_star_similarity()`, `_llm_should_merge()` | Two-stage deduplication (rule + LLM) |
| `task_clustering.py` | `_extract_task_title()`, `_detect_status()`, `_is_noise_task()` | Title extraction, status detection, noise filtering |
| `star_builder.py` | `build_stars_for_tasks()`, `build_star_for_task()` | STAR extraction orchestration |
| `star_builder.py` | `_llm_enrich()`, `_call_llm()`, `_parse_json_response()` | LLM API call for STAR extraction |
| `star_builder.py` | `_apply_save_conversation()`, `_compute_cache_key()` | Historical runtime recap integration, caching |
| `report_renderer.py` | `render_weekly_report()`, `_render_task()` | Markdown report generation |
| `report_renderer.py` | `save_report()` | File I/O, directory creation |
| `cron_wrapper.sh` | `source env`, `exec python` | Cron environment setup and execution |

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Time gap threshold | 120 minutes (not 30) | Accommodate lunch breaks, context switching |
| Similarity weights | Situation 0.5 > Task 0.3 > Result 0.2 | Situation captures shared context best |
| LLM model for merge | Haiku 4.5 | Fast, cheap, sufficient for yes/no judgment |
| LLM model for STAR | Sonnet 4.6 | Higher quality for structured extraction |
| Cache strategy | SHA256(task_id + conversation[:2000]) | Trades precision for speed; false cache miss acceptable |
| Title for pre-merge | Yes; for STAR similarity | No | Title is user-generated and inconsistent |
| Report format | Markdown | Portable, version-control friendly, easy to read |
