---
name: post-mortem
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
   - `值得沉淀` — Patterns worth capturing as a rule / skill / wiki.
5. **沉淀**（如果是「值得沉淀」）— Where to put it: `.agent-state/rules/mistakes.md`?
   A new skill? Wiki?

## Writing Rules

- 说人话。No "此外"、"值得注意的是"、"综上所述"、"显著提升".
- 用断言句。"改了三行代码" not "进行了相关调整".
- 数字和文件名前置。"`server.py` 第 87 行超时设了 5 秒" not "超时配置方面做了优化".
- 每个尝试说清"为什么不行"，不是"尝试了方案 A，不可行".
