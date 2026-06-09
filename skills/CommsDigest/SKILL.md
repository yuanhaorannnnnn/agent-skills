---
name: CommsDigest
description: |
  Load when the user shares a discussion thread and wants to visualize its
  structure, or says "梳理这个讨论", "这条线程结论是什么", "理一下参与人立场",
  "digest this thread", "summarize this email chain", "这个 GitHub issue 到底
  决定了什么". Handles email threads, GitHub issues/PRs, chat logs, and forum
  posts. Output is an interactive HTML visualization, not a markdown note.
version: "2.0.0"
user_invocable: true
---

# Discussion Digest: 讨论线程可视化梳理

从多人讨论中提取决策结构，输出为交互式 HTML 可视化页面。

## 架构：两阶段管线

```
Phase 1: 讨论分析（AI 语义理解）
  原始讨论文本
    → 结构化 JSON（按固定 schema）
    → 保存为 raw/discussions/<slug>.json

Phase 2: HTML 渲染（脚本化，零 AI）
  raw/discussions/<slug>.json
    → scripts/render_discussion.py
    → queries/<slug>.html
```

## Phase 1: 讨论分析

### Step 1.1: 获取讨论内容

- GitHub issue/PR URL：`gh issue view` / `gh pr view` 获取讨论内容
- 邮件/聊天/论坛：直接读取用户粘贴的文本
- 网页 URL：WebFetch 获取内容

### Step 1.2: 生成结构化 JSON

按 `references/schema.md` 的 schema 分析讨论，输出 JSON。**必须先读 schema 再生成。**

关键约束：
- participants[].role 必须是枚举值：OP / Core / Reviewer / Commenter / Observer
- timeline 最多 30 条，is_key 条目 ≤ 8 个
- decisions 至少 1 条，没有明确结论写"无明确结论"
- unresolved 不能空
- 所有 name/author 使用原始显示名，不翻译

### Step 1.3: 保存 JSON artifact

```bash
mkdir -p raw/discussions
```

写入 `raw/discussions/<slug>.json`。如果用户没说 slug，从讨论标题/source 生成。

## Phase 2: HTML 渲染

```bash
python3 ~/.claude/skills/CommsDigest/scripts/render_discussion.py raw/discussions/<slug>.json -o queries/<slug>.html
```

渲染器完全脚本化——JSON → HTML 模板注入，零 AI 参与。模板位于 `templates/discussion-digest.html`。

## Canon promotion

读取共享契约：`/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md`。

- `queries/{slug}.html` 是讨论可视化 artifact
- `raw/discussions/{slug}.json` 是可审计的中间产物
- 讨论中形成的决定、争议、action items 进入 Canon `decisions/`、`tasks/`、`patterns/` 或 `raw/update-cards/`
- 创建或更新 `/media/yhr/2T/Canon/raw/update-cards/<date>-commsdigest-<slug>.md`

## 与 content-ingest 的区别

| 维度 | content-ingest | discussion-digest |
|------|---------------|-------------------|
| 输入 | 单人叙述（视频/文章） | 多人对话（线程/issue/聊天） |
| 提取目标 | 可操作知识（how） | 决策过程（who decided what） |
| 输出格式 | Markdown → queries/ | JSON → HTML → queries/ |
| 核心问题 | "这篇文章讲了什么有用的" | "这群人到底怎么决定的" |

## 依赖

- Python 3.9+（Phase 2 渲染器）

## 资源

- `references/schema.md`：JSON schema 规范（Phase 1 输出契约）
- `scripts/render_discussion.py`：JSON → HTML 渲染器（Phase 2）
- `templates/discussion-digest.html`：HTML 设计系统模板
