---
name: after-action
description: |
  Use only after a concrete defect, failure, or difficult technical problem has
  been resolved and the useful output is its incident-specific troubleshooting
  story: symptom, diagnosis, failed attempts, root cause, final fix, and whether
  it is truly resolved. Trigger on "故障复盘", "debug 复盘", "怎么修好的",
  "fix log", "写一份修复记录", "post-mortem", or "记录一下这个 bug 的解决过程".
  Do not use when the user only wants one reusable guardrail; use codify. Do not
  use for a formal end-to-end report on an entire completed task; use sanitize
  report mode.
---

# Post-Mortem

Write like you're leaving a note for your future self who will hit the same
problem in 6 months. Human language, no AI slop. Specifics over summaries.

## Boundary

Require a specific incident or difficult problem plus diagnosis/fix evidence. Preserve the chronology and failed attempts. Route a standalone reusable rule to codify; route a full completed-deliverable report with implementation and evaluation to `sanitize report`.

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

## 沉淀前强制自问（Prevention Gate）

沉淀节动手前，逐条回答三问。答不出来不许写规则：

1. 触发条件：什么时候会再犯？（必须具体，如“对动力学参数做 A/B 时”）
2. 动作：该做什么？（必须可执行，如“先断言初始速度≈0”）
3. 可检查结果：怎么知道做没做？（如“测试第一条日志必须显示 v=0”）

路由判定（按顺序命中即停）：

- 三问全答出，且规则是**单条命令句** → 调 codify 存为 guardrail。
- 三问全答出，但是**多步流程** → 沉淀为 Canon pattern / checklist / 脚本工具，不调 codify。
- 答不出，或规则写成后是空话 → 沉淀节只保留事故记录，标注“无新增预防项”，不强行 codify。

反膨胀原则：不为写规则而写规则。颗粒度太小的伪规则（一次事故一条、下次不会触发）直接丢弃；规则质量优先于规则数量。历史教训：guardian/autoreview 曾因堆积大量细粒度 rule 造成上下文与审核量膨胀。

参考依据：wiki 仓库 `queries/20260730-codex-custom-code-review-rules.md` 与
`raw/config/20260723-codex-default.rules`（Codex custom rules 优化任务）——
规则只写 consequential、non-obvious 的不变量；删除后 review 结果不变的规则
不值得常驻；能写成测试 / lint / checklist / 脚本的约束，不占规则位。

## Case Share Page

When the user asks for case share, 分享, 培训, 复盘页面, or a page for other people:

1. Write the 5-section after-action record first.
2. Call `breach` to turn it into a single-page HTML artifact.
3. Prefer html-effectiveness `12-incident-report`; use `14-research-feature-explainer` only when the case is more educational than incident-like.
4. Put the reusable rule, if any, in the final section and trigger `codify` only when it deserves a durable rule.

## Canon 输出边界

读取共享契约：`/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md`。

- after-action 文本是修复记录 artifact；长期根因、失败尝试、防错规则和复用模式优先沉淀到 Canon `incidents/` 或 `patterns/`。
- 复杂修复完成后，创建或更新 `/media/yhr/2T/Canon/raw/update-cards/<date>-afteraction-<topic>.md`，引用修复记录、commit、日志和验证证据。
- 如果调用者是 `repair Fix`，同时更新对应 `/media/yhr/2T/Canon/tasks/<bug-id>.md`。
- 如果生成了 case share HTML，也把 breach 页面路径或 URL 作为 artifact ref 记录。

## Writing Rules

- 说人话。No "此外"、"值得注意的是"、"综上所述"、"显著提升".
- 用断言句。"改了三行代码" not "进行了相关调整".
- 数字和文件名前置。"`server.py` 第 87 行超时设了 5 秒" not "超时配置方面做了优化".
- 每个尝试说清"为什么不行"，不是"尝试了方案 A，不可行".

## Gate

写入后跑：
```bash
python3 <skill-dir>/scripts/aar_gate.py <report.md>
```
blocked → 缺节或未选判断。4 项：文件存在、5 节完整、判断选了三选一、禁词命中（warn）。
