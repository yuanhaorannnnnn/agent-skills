# Formal Report Contract

Use this mode only for a formal, evidence-backed Markdown report covering an
entire completed task or deliverable end to end. Require task-wide scope plus
implementation and validation evidence.

## Source Priority

1. `/media/yhr/2T/Canon/tasks/<task>.md`
2. linked commits, test/build results, reports, logs, and artifacts
3. `.planning/conversations/` and `.agent-state/conversations/` as historical
   secondary evidence
4. current repository state for implementation facts

Build from repository evidence, not memory. If evidence is insufficient, state
the gap and do not upgrade an unverified claim into a result.

## Structure

1. **Abstract** — background, problem, approach preview, key outcome
2. **Related Works** — alternatives considered and why rejected
3. **Method** — final technical selection, rationale, constraints, tradeoffs
4. **Implementation** — code architecture, module organization, data flows
5. **Evaluation** — tests, results, benchmarks, acceptance-criteria comparison
6. **Conclusion and Future Work** — outcome, remaining risks, next steps

## Rules

- Keep scope on the completed task, not the whole repository.
- Trace each claim to a Canon task page, planning record, commit, test, or other
  explicit evidence.
- Preserve the distinction between implemented, statically checked, built,
  runtime tested, benchmarked, and not yet verified.
- Save the report as a repo-local artifact unless the user specifies a path.
- Record the artifact path in Canon; promote durable decisions and remaining
  work, not a duplicate copy of the report.
- A report covering only one defect's troubleshooting chronology belongs to
  AfterAction.
- A result expressible as wrong/correct/trigger belongs to Codify.
