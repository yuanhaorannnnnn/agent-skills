---
name: FieldReport
description: |
  Use only for a formal, evidence-backed Markdown report covering an entire
  completed task or deliverable end to end: rationale, implementation,
  evaluation, outcome, and remaining work. Trigger on "完整任务技术报告",
  "完成后的技术总结", "成果汇报", "post-task report", or a research report
  for completed work. Source the report from Canon task pages, planning records,
  commits, and validation evidence. Do not use for one bug's troubleshooting
  story; use AfterAction. Do not use for one reusable guardrail; use Codify. Do
  not use while implementation is active unless the user explicitly requests an
  interim formal report.
---

# Report

Generate a 6-section technical report in academic paper structure, built from
Canon task pages (`/media/yhr/2T/Canon/tasks/<task>.md`) as the primary source,
with `.planning/conversations/` and `.agent-state/conversations/` as secondary
historical evidence.

## Boundary

Require task-wide scope and both implementation and validation evidence. A report that only explains one failure belongs to AfterAction. A result that can be expressed as wrong/correct/trigger belongs to Codify.

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

## Gate

报告完成后跑：
```bash
python3 ~/.claude/skills/FieldReport/scripts/source_gate.py <report.md>
```
blocked → 缺节或缺源。3 项：文件存在且 ≥200 字、6 节完整、引用了至少一个 Canon task / planning doc / commit。pass → 继续 Canon promotion。
