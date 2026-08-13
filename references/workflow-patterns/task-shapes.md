# Local Task Shapes

Map local skills and workflows to workflow patterns.

## repair

### Intake

- Shape: classify-and-act.
- Why: decide whether this is fixable, false positive, cannot reproduce, blocked, or requirement.
- Output: fix plan, breach incident page, Yunxiao status.

### Fix

- Shape: fan-out-and-synthesize + adversarial-verification for uncertain root cause.
- Add loop-until-done around monitored build/test when failures are iterative.
- Avoid fan-out for narrow obvious fixes.

## tasking

### Orient

- Shape: fan-out-and-synthesize.
- Workers: PRD/user behavior, code architecture, API/data contract, risk/assumption scan.
- Synthesis: conops design doc.

### Briefing

- Shape: classify-and-act.
- Route people/date/calendar/document failures before creating events.

## traceback

- Shape: fan-out-and-synthesize + adversarial-verification.
- Workers: design claims, implementation mapping, test coverage.
- Verifier: challenge matches that are inferred but weak.

## breach

- Shape: classify-and-act + adversarial-verification.
- Classify page type from html-effectiveness catalog.
- Verify provenance footer/comment and DESIGN.md style source before accepting output.

## after-action

- Shape: structured synthesis.
- When case share is requested, call breach after the 5-section record.
- Trigger codify only for reusable durable rules.

## passdown / Canon Resume

- Shape: classify-and-act.
- Route by source runtime, directory, focus, and artifact availability.
