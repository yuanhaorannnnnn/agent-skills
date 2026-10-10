# conops: review-ready technical design documents

`conops` turns an agreed problem, its constraints, and available implementation
evidence into a design document (`md | html | both`, default `md`) for product, development, and test
review. It answers **how the change works and why that choice is acceptable**;
it is a technical design document, not a PRD or a feature announcement.

The complete execution contract is [`SKILL.md`](SKILL.md). This README is a
short guide to the reasoning shape and the handoff boundary.

`conops` owns the technical-design content workflow; `breach` owns general HTML
presentation. They compose by responsibility rather than split content topics.
Invoke `conops` only when the task calls for a technical design, regardless of
`md | html | both`. A test report or discussion does not invoke `conops` merely
because it is presented as HTML.

## The design spine

Keep the document readable as one chain:

```text
constraints → decision → mechanism → trade-offs → verification
```

- **Constraints** state the user-visible goal, compatibility limits, existing
  interfaces, excluded scope, and evidence gaps. Mark unresolved parameters as
  open questions instead of inventing defaults.
- **Decision** states the selected behavior and the alternatives rejected. A
  review should be able to approve or reject this sentence directly.
- **Mechanism** maps the decision to flow, data, interfaces, core logic, and
  concrete code locations. Include units, defaults, states, and failure
  behavior where they are part of the contract.
- **Trade-offs** name the cost, risk, or limitation introduced by the choice
  and the mitigation or follow-up boundary. Do not turn a limitation into a
  performance or product claim without evidence.
- **Verification** turns the decision into review points, layered tests, and
  acceptance criteria. Separate static checks, offline measurements, and real
  runtime evidence.

## A compact review-ready example

The following is a shape example, not a claim about an existing product:

```text
Constraint: Existing clients consume one timestamped frame type; the first
release must preserve that contract and must not add a second transport.

Decision: Add the new measurement as an optional field on the existing frame;
when unavailable, retain the current field value and expose an explicit state.

Mechanism: Validate configuration at startup, populate the field in the frame
assembly path, propagate the state through serialization, and keep old clients
validating the unchanged required fields.

Trade-off: One frame carries more conditional data, so payload size and the
unavailable state need explicit limits and compatibility tests.

Verification: Check schema compatibility, startup rejection of invalid input,
field/state behavior for available and unavailable data, and a runtime frame
sequence with timestamps and units.
```

The real document should replace this shape with observed paths, exact field
names, measured values, and evidence-backed acceptance criteria.

## Suggested document flow

Use the full section contract from [`SKILL.md`](SKILL.md), while keeping each
section decision-oriented:

1. State the problem and the one-sentence decision.
2. Make included and excluded scope explicit; exclusions should be at least as
   concrete as inclusions.
3. Describe user-visible behavior before internal architecture.
4. Show the flow and data model, then explain the core logic and failure paths.
5. Give product and test reviewers choices and test cases, not assignments.
6. End with acceptance criteria, risks, code navigation, current status, and a
   checkbox decision record.

Save the selected artifact according to the development repository's AGENTS.md
and documentation layout. CARLA uses `Docs/tasks/<slug>/design.md`; repositories
without a documented layout retain the `.proposal/<slug>/` default. Do not silently promote it to a different repository or treat a
prepared document as an approved decision. The shared output boundary is
documented in [`canon-output-contract.md`](../../references/canon-output-contract.md).

## Evidence and scope boundary

Conversation decisions and the current task contract establish intent. Existing
code and referenced files establish implementation facts. Runtime commands and
measurements establish runtime facts. Keep those categories distinguishable;
absence of a measurement is not a passing result. Use the CARLA-specific
constraints only when that domain applies, from
[`carla-sensor-design.md`](references/carla-sensor-design.md).

Run the bundled quality gate against the finished document:

```bash
python3 skills/conops/scripts/quality_gate.py <path-to-design-doc.md-or-index.html>
```

The gate checks structure, prohibited wording, scope balance, and common
review-language problems. Human review still owns factual accuracy, path
navigation, evidence strength, and whether the acceptance criteria can actually
be executed.

## Boundary with `breach`

`conops` owns facts, scope, architecture, acceptance criteria, and review
decisions. Output format is a delivery choice:

- `md` (default): save, check, and deliver Markdown.
- `html`: approve the content contract, then call `breach` General page mode;
  check and deliver HTML directly. No Markdown file or extra Markdown delivery
  is required. A natural-language HTML-only request selects this mode.
- `both`: Markdown is the maintenance source; HTML derives from the same
  approved prose. Check both artifacts and regenerate HTML after prose changes.

Hand approved prose, target project, output path, and content mode to
[`breach`](../breach/README.md). `breach` owns layout, visual integration,
rendering, and provenance; it must not rewrite the approved technical conclusion
or make static HTML stand in for runtime evidence.

HTML retains all 14 sections as `h1`–`h6` headings and uses scope subheadings
with `ul`/`ol` lists. The gate reads static HTML text, headings, and list items;
it ignores head metadata, scripts, styles, and comments, and does not execute
JavaScript or compute CSS visibility. Breach visual checks remain required.
Use the same task directory for both formats (`index.html` by default for HTML),
subject to explicit project or caller paths.
