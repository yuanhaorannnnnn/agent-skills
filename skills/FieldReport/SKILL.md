---
name: FieldReport
description: |
  Generate a Markdown technical report in academic paper structure for a
  completed task. Use this skill whenever the user asks for a 技术报告,
  技术总结, 方案汇报, research report, or post-task documentation — even if
  they don't explicitly name the skill. Accepts an optional `--conversation`
  parameter to identify the task thread, just like `save-conversation` and
  `restore-conversation`. Sources material from
  `.planning/conversations/<conversation>/` and
  `.agent-state/conversations/<conversation>.md` by default. Do not use while
  the task is still actively being implemented unless the user explicitly wants
  a report artifact at that moment.
---

# Report

Generate a 6-section technical report in academic paper structure, built from
`.planning/conversations/<id>/` and `.agent-state/conversations/<id>.md`.

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
