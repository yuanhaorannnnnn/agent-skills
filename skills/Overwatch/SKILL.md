---
name: Overwatch
description: |
  快速理解代码区域的全貌——不是深入研究，而是"给我看看这块代码在地图上的位置"。
  触发词："zoom out"、"拉远看"、"给我看看整体结构"、"这段代码在整个项目里是什么位置"、
  "这个模块被哪些地方调用了"、"大图是什么"。
  disable-model-invocation: true——只在用户明确需要俯瞰视角时手动触发。
---

I don't know this area of code well. Go up a layer of abstraction.
Give me a map of all the relevant modules and callers, using the
project's domain glossary vocabulary. Do NOT dive into implementation
details — this is about orientation, not deep analysis.

## Canon 输出边界

读取共享契约：`/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md`。

- Code overview findings are normally conversational context. Promote to Canon only when the overview establishes durable project architecture, pattern, or task state.
- Canon update-card path, when needed: `/media/yhr/2T/Canon/raw/update-cards/<date>-overwatch-<topic>.md`.
