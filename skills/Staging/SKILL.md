---
name: Staging
status: deprecated
description: |
  DEPRECATED — functionality absorbed by Execute --plan.
  See /home/yhr/.agents/repos/agent-skills/skills/Execute/references/plan-template.md
  for the plan structure template previously provided by this skill.
---

# DEPRECATED — Plan Workspace

Staging has been deprecated. Its three-file planning framework (shape → task_plan → findings → progress) is now provided by `Execute --plan`, which writes the same structure directly into Canon task page sections (§ Plan / § Findings / § Progress).

## Migration

| Old (Staging) | New (Execute --plan) |
|---------------|----------------------|
| `.planning/conversations/<id>/shape.md` | Canon task page § Goal |
| `.planning/conversations/<id>/task_plan.md` | Canon task page § Plan |
| `.planning/conversations/<id>/findings.md` | Canon task page § Findings |
| `.planning/conversations/<id>/progress.md` | Canon task page § Progress |

## Reference

The plan structure template lives at:

```text
/home/yhr/.agents/repos/agent-skills/skills/Execute/references/plan-template.md
```

This file is kept for backward reference only. Do not trigger on this skill.
