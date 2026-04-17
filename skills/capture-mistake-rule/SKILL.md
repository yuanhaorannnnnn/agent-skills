---
name: capture-mistake-rule
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
3. Check `.agent-state/rules/mistakes.md` for duplicates before writing the raw incident record.
4. Append the raw incident rule if it is materially new.
5. If the rule is reusable beyond one isolated incident, also promote it into
   `.agent-state/rules/mistakes.md` as a durable repo-level pattern.

## Promotion Rule

Promote a mistake into `.agent-state/rules/mistakes.md` when at least
one of these is true:

- it has happened more than once
- it affects multiple skills or workflows
- it is a process-level guardrail, not just a local typo
- it belongs in the repo-local agent system as a long-term rule

Keep one-off or purely local mistakes only in `.agent-state/rules/mistakes.md`.

## Script

Use `../.scripts/note_rule.py` for deterministic updates. The script records
the raw incident in `.agent-state/rules/mistakes.md`.
