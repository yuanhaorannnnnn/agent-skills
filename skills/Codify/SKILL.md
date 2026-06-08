---
name: Codify
description: |
  Use when a mistake, misread requirement, repeated implementation error, or
  important lesson should be recorded as a durable rule so it is not repeated.
  Trigger on requests like "write this down as a rule", "remember this mistake",
  "capture a lesson learned", or "add a guardrail for next time".
---

# Capture Mistake Rule

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
