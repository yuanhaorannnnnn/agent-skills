---
name: discussion-digest
description: |
  Load when the user shares a discussion thread and wants to visualize its
  structure, or says "梳理这个讨论", "这条线程结论是什么", "理一下参与人立场",
  "digest this thread", "summarize this email chain", "这个 GitHub issue 到底
  决定了什么". Handles email threads, GitHub issues/PRs, chat logs, and forum
  posts. Output is an interactive HTML visualization, not a markdown note.
version: "1.0.0"
user_invocable: true
---

# Discussion Digest: 讨论线程可视化梳理

从多人讨论中提取决策结构，输出为交互式 HTML 可视化页面。

## 与 content-ingest 的区别

| 维度 | content-ingest | discussion-digest |
|------|---------------|-------------------|
| 输入 | 单人叙述（视频/文章） | 多人对话（线程/issue/聊天） |
| 提取目标 | 可操作知识（how） | 决策过程（who decided what） |
| 输出格式 | Markdown → queries/ | HTML → queries/ |
| 核心问题 | "这篇文章讲了什么有用的" | "这群人到底怎么决定的" |

## 输入格式

- GitHub issue / PR 讨论（URL 或粘贴文本）
- 邮件线程（粘贴原文）
- 聊天记录（微信/Slack/Discord 导出）
- 论坛帖子（URL 或粘贴文本）

## 提取三层

### 1. 参与方

| 维度 | 说明 |
|------|------|
| 参与者列表 | 谁参与了讨论 |
| 初始立场 | 每个人一开始持什么观点 |
| 立场变化 | 谁在哪个时间点改变了立场，为什么 |
| 关键发言 | 每人的代表性发言（1-2 句摘录） |

### 2. 时间线

- 按时间排列的关键事件
- 标注转折点：什么信息/论据导致讨论走向改变
- 区分"Matter-of-fact 信息提供"和"Opinion 立场表达"

### 3. 结论

- 最终决定 / 达成的共识
- 未解决的争议（ongoing disagreement）
- 待办事项（action items / who owns what）
- 如果有投票，记录票型和结果

## 工作流

### Step 1: 获取讨论内容

- 如果是 GitHub URL：用 `gh issue view` / `gh pr view` 获取讨论内容（含评论）
- 如果是邮件/聊天/论坛：直接读取用户粘贴的文本
- 如果是网页 URL：WebFetch 获取内容

### Step 2: 阅读理解

按三层框架阅读全部讨论内容。关注：
- 谁先提出什么 → 谁反对/支持 → 什么信息改变了讨论走向
- 区分"被解决的问题"和"被绕过的分歧"
- 如果讨论很长，先扫描全貌再精读关键段

### Step 3: 生成交互式 HTML 可视化

输出到 `queries/{slug}.html`，使用内置的 HTML 模板（见下方），包含：
- 可折叠的参与方卡片（立场+代表发言+立场变化）
- 垂直时间线（事件+转折点标注）
- 结论摘要面板
- 配色干净、适合在浏览器中阅读

HTML 模板位于 `templates/discussion-digest.html`。使用时将数据填入模板的占位符区域。

### Step 4: 更新索引

在 `index.md` Queries 区追加条目，`log.md` 追加记录，`raw/PROCESSED.md` 追加标记。

## 依赖

无外部脚本依赖。纯 LLM 阅读理解 + HTML 模板渲染。

## 资源

- `templates/discussion-digest.html`：交互式 HTML 模板
