---
name: FieldReport
description: |
  Generate a Markdown technical report in academic paper structure for a
  completed task. Use this skill whenever the user asks for a 技术报告,
  技术总结, 方案汇报, research report, or post-task documentation — even if
  they don't explicitly name the skill. Accepts an optional task page path or
  slug to identify the task. Sources material from
  `/media/yhr/2T/Canon/tasks/<task>.md` (primary) and
  `.planning/conversations/` / `.agent-state/conversations/` (historical
  runtime buffers, secondary) by default. Do not use while
  the task is still actively being implemented unless the user explicitly wants
  a report artifact at that moment.
---

# Report

Generate a 6-section technical report in academic paper structure, built from
Canon task pages (`/media/yhr/2T/Canon/tasks/<task>.md`) as the primary source,
with `.planning/conversations/` and `.agent-state/conversations/` as secondary
historical evidence.

## Canon 输出边界

读取共享契约：`/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md`。

- `.planning/` 和 `.agent-state/` 是报告证据源，不是报告后的长期 source of truth。
- 技术报告本身是 artifact；默认保存到用户指定路径或当前 repo 合适目录，并在 Canon `artifacts/` 或 update-card 中引用绝对路径。
- 已完成任务的长期结论应更新 Canon task/project/decision/pattern/incident 页面。
- 若证据不足只生成临时报表，最终回复要说明未做 Canon promotion。

## Structure

1. **Abstract** — background, problem, approach preview, key outcome
2. **Related Works** — alternatives considered, why rejected
3. **Method** — final technical selection, rationale, constraints and tradeoffs
4. **Implementation** — code architecture, module organization, data flows
5. **Evaluation** — how it was tested, results, benchmarks, vs acceptance criteria
6. **Conclusion and Future Work** — summary, remaining risks, next steps

## Rules

- Build from repository evidence, not memory. If evidence is insufficient, say so.
- Keep it narrow — about the task, not the whole repository.
- Every claim traces back to a planning doc, commit, test result, or decision record.
- Do not use while the task is still being implemented unless explicitly asked.
- After producing a non-trivial report, create/update `/media/yhr/2T/Canon/raw/update-cards/<date>-fieldreport-<topic>.md` with report path, source evidence, claims, and follow-ups.
