---
name: Codify
description: |
  Use only when the desired output is one compact, reusable guardrail that
  prevents a mistake from recurring. Trigger on "write this down as a rule",
  "remember this mistake", "capture a lesson learned", or "add a guardrail for
  next time". Do not use for a narrative of one incident or debugging journey;
  use AfterAction. Do not use for an end-to-end report on a completed task; use
  FieldReport.
---

# Capture Mistake Rule

## Boundary

Produce a rule, not a story or report. The minimum useful output is wrong approach, correct approach, trigger, and evidence. If incident chronology matters, route to AfterAction. If the full task lifecycle and evaluation matter, route to FieldReport.

## Workflow

1. Summarize the mistake in one sentence.
2. Convert it into a compact rule with:
   - incorrect approach
   - correct approach
   - trigger scenario
3. Check Canon `patterns/` and `incidents/` first, then check repo-local `.agent-state/rules/mistakes.md` for compatibility duplicates.
4. Append the raw incident record if it is materially new.
5. If the rule is reusable beyond one isolated incident, promote it to Canon `patterns/` or `incidents/`; repo-local `.agent-state/rules/mistakes.md` is a project compatibility mirror.

## Promotion Rule

Promote a mistake into Canon when at least
one of these is true:

- it has happened more than once
- it affects multiple skills or workflows
- it is a process-level guardrail, not just a local typo
- it belongs in the cross-project Canon graph as a long-term rule

Keep one-off or purely local mistakes only as raw incident entries in repo-local `.agent-state/rules/mistakes.md`. Do not elevate them into Canon patterns.

## Canon 输出边界

读取共享契约：`/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md`。

- Durable rules go to Canon `patterns/` or `incidents/`; repo-local `.agent-state/rules/mistakes.md` remains a runtime compatibility mirror.
- For each materially new reusable rule, create or update `/media/yhr/2T/Canon/raw/update-cards/<date>-codify-<slug>.md` with wrong/correct/trigger/evidence.
- If the rule is project-specific only, update the project page or local rule file and state that no cross-project Canon pattern was created.

## Script

Use `~/.agents/skills/.scripts/note_rule.py` for deterministic repo-local compatibility updates. The script records the raw incident in `.agent-state/rules/mistakes.md`; Canon promotion is the durable step.
