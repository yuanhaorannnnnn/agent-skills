# Workflow Pattern Hub

Use this hub when a task is high-risk, unclear, parallelizable, adversarial, long-running, or likely to drift in one context window.

This is a pattern-selection reference, not a skill and not a runtime. It helps an agent choose a task harness before execution.

Source seed:

```text
/media/yhr/2T/files/wiki/raw/clippings/A harness for every task dynamic workflows in Claude Code 适用于各种任务的工具：Claude Code 中的动态工作流.md
```

## Core Distinction

```text
Skill = reusable doctrine and workflow entry
Workflow pattern = execution harness shape for this task
Canon = durable memory graph and artifact index
```

Do not use workflow patterns for ordinary small coding tasks. Extra orchestration costs tokens and can add noise.

## Selection Table

| Task shape | Symptoms | Start with | Add when needed |
|---|---|---|---|
| Unclear task type | Input needs routing before action | `classify-and-act` | `model-routing` |
| Many independent items | Files, claims, tickets, sessions, candidates | `fan-out-and-synthesize` | `adversarial-verification` |
| High risk verification | Need proof, not confidence | `adversarial-verification` | `loop-until-done` |
| Many ideas or names | Need options then selection | `generate-and-filter` | `tournament` |
| Competing solutions | Several approaches can solve same task | `tournament` | `adversarial-verification` |
| Unknown amount of work | Continue until no new findings/errors | `loop-until-done` | `fan-out-and-synthesize` |
| Untrusted input | Public tickets, resumes, Slack, web text | `quarantine` | `classify-and-act` |
| Model/tool cost varies | Need route by complexity | `model-routing` | `classify-and-act` |

## Minimal Selection Protocol

1. Name the task shape in one sentence.
2. Pick one primary pattern; add at most one secondary pattern.
3. Define the stop condition before spawning work.
4. Define the output schema before synthesis.
5. Record artifacts and durable conclusions through Canon when they matter.

## References

- [patterns.md](patterns.md) — pattern recipes.
- [task-shapes.md](task-shapes.md) — mappings to local skills and workflows.
- [examples.md](examples.md) — reusable prompt shapes and local cases.
