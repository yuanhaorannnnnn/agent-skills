# Review Checklist

## Correctness

- Does the changed logic match the code's literal behavior?
- Are null, empty, boundary, and zero-value cases handled?
- Are state changes and side effects intentional?
- Are error paths and fallback paths covered?

## Security

- Are external inputs validated before use?
- Are there command, path, or injection risks?
- Are secrets or environment-specific values hardcoded?

## Maintainability

- Do names reveal intent?
- Is there duplicated logic that should be centralized?
- Are magic numbers or ad hoc strings introduced without explanation?
- Does the change respect existing architecture captured in `.agent-state/MEMORY.md`?

## Performance

- Does the change add avoidable repeated work?
- Are expensive operations placed in hot loops?

## Reporting Rules

- Findings first, ordered by severity
- Each critical or warning item includes a concrete fix direction
- If there are no findings, say so explicitly
