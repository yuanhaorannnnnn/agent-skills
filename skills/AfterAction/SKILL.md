---
name: AfterAction
description: |
  Lightweight problem-solving debrief — not an academic report, not a blame
  document. After fixing a complex or long-running issue, write a concise
  "what happened, what we tried, what worked, is it really fixed" record
  for your future self.

  Trigger on: "post-mortem", "post mortem", "复盘", "问题解决记录",
  "debug 总结", "怎么修好的", "fix log", "写一份修复记录",
  "故障复盘", "事后分析", "记录一下这个 bug 的解决过程".
---

# Post-Mortem

Write like you're leaving a note for your future self who will hit the same
problem in 6 months. Human language, no AI slop. Specifics over summaries.

## Structure (5 sections, no more)

1. **背景** — What broke, when, and why it mattered. One sentence + one
   concrete observable symptom.
2. **踩过的坑** — What you tried that DIDN'T work. Each attempt: what you
   did, why you thought it would work, and why it actually didn't. These
   are the most valuable parts — they save the next person from retrying.
3. **最终方案** — What actually fixed it. Keep it short: the key change,
   the critical insight, the one thing that mattered. Code snippet if it
   helps (≤10 lines).
4. **判断** — Pick ONE:
   - `临时 hack` — Works now, needs revisiting. What's the real fix?
   - `彻底修复` — Root cause addressed, won't recur.
   - `值得沉淀` — Patterns worth capturing as a Canon pattern/incident, repo-local rule, or skill.
5. **沉淀**（如果是「值得沉淀」）— Canon target first: `patterns/`, `incidents/`, `tasks/`, or `raw/update-cards/`; repo-local `.agent-state/rules/mistakes.md` is compatibility only.

## Case Share Page

When the user asks for case share, 分享, 培训, 复盘页面, or a page for other people:

1. Write the 5-section AfterAction record first.
2. Call `Breach` to turn it into a single-page HTML artifact.
3. Prefer html-effectiveness `12-incident-report`; use `14-research-feature-explainer` only when the case is more educational than incident-like.
4. Put the reusable rule, if any, in the final section and trigger `Codify` only when it deserves a durable rule.

## Canon 输出边界

读取共享契约：`/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md`。

- AfterAction 文本是修复记录 artifact；长期根因、失败尝试、防错规则和复用模式优先沉淀到 Canon `incidents/` 或 `patterns/`。
- 复杂修复完成后，创建或更新 `/media/yhr/2T/Canon/raw/update-cards/<date>-afteraction-<topic>.md`，引用修复记录、commit、日志和验证证据。
- 如果调用者是 `Repair Fix`，同时更新对应 `/media/yhr/2T/Canon/tasks/<bug-id>.md`。
- 如果生成了 case share HTML，也把 Breach 页面路径或 URL 作为 artifact ref 记录。

## Writing Rules

- 说人话。No "此外"、"值得注意的是"、"综上所述"、"显著提升".
- 用断言句。"改了三行代码" not "进行了相关调整".
- 数字和文件名前置。"`server.py` 第 87 行超时设了 5 秒" not "超时配置方面做了优化".
- 每个尝试说清"为什么不行"，不是"尝试了方案 A，不可行".
