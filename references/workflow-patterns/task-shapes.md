# Local Task Shapes

Map local skills and workflows to workflow patterns.

## Repair

### Intake

- Shape: classify-and-act.
- Why: decide whether this is fixable, false positive, cannot reproduce, blocked, or requirement.
- Output: fix plan, Breach incident page, Yunxiao status.

### Fix

- Shape: fan-out-and-synthesize + adversarial-verification for uncertain root cause.
- Add loop-until-done around Sentinel build/test when failures are iterative.
- Avoid fan-out for narrow obvious fixes.

## Tasking

### Orient

- Shape: fan-out-and-synthesize.
- Workers: PRD/user behavior, code architecture, API/data contract, risk/assumption scan.
- Synthesis: CONOPS design doc.

### Briefing

- Shape: classify-and-act.
- Route people/date/calendar/document failures before creating events.

## Traceback

- Shape: fan-out-and-synthesize + adversarial-verification.
- Workers: design claims, implementation mapping, test coverage.
- Verifier: challenge matches that are inferred but weak.

## DoctrineReview

- Shape: fan-out-and-synthesize + generate-and-filter + adversarial-verification.
- Mine sessions, cluster repeated corrections, filter to real reusable candidates, then Codify survivors.

## Breach

- Shape: classify-and-act + adversarial-verification.
- Classify page type from html-effectiveness catalog.
- Verify provenance footer/comment and DESIGN.md style source before accepting output.

## AfterAction

- Shape: structured synthesis.
- When case share is requested, call Breach after the 5-section record.
- Trigger Codify only for reusable durable rules.

## Fusion

- Shape: fan-out-and-synthesize for deep research.
- Add adversarial-verification for claims that will influence decisions.

## Sweep / Calibrate

- Shape: loop-until-done.
- Add model-routing when optimization hypotheses vary in complexity.
- Stop on benchmark, test, or budget condition.

## Passdown / Reactivate

- Shape: classify-and-act.
- Route by source runtime, directory, focus, and artifact availability.
