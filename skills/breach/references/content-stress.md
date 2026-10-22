# General page content stress checks

Find layouts that work only with convenient sample data. Test the existing
page with plausible boundary values; do not redesign it or invent new widgets
to increase coverage. A simple fixed-content reading page need not run a full
matrix unless requested.

## Protect the deliverable

Record the delivery file's SHA-256 before testing. For a standalone HTML page,
copy it into a temporary directory and replace only content values in that
copy, preserving structure, CSS and behavior. For a data-driven page, use its
fixture, props or mock API boundary in an isolated preview. Do not edit the
live DOM/CSS merely to manufacture a layout failure. Do not persist real API
mutations, synthetic data, test toggles or preview scripts in the delivery file.

Keep fixtures and evidence separate from the deliverable, clearly labelled
synthetic. Use temporary directories that are removed even on failure. Prefer
an unchanged real-content case and separate fresh copies for each stress case
over trying to restore a mutated page in place. Do not serialize the stressed
browser DOM back into the original HTML.

After the run, verify the delivery hash again, including failed runs. A mismatch
is a failed preservation check: stop delivery and inspect the diff; do not
blindly restore a backup over potentially concurrent user edits. If a layout
fix is authorized, apply only that fix to the real-content page, review its
diff, establish a new baseline, and rerun the affected cases.

## Select relevant content cases

Map visible fields to their actual source, type, optionality and known limit.
Use schema/API limits where available; otherwise mark the limit unknown and
use a plausible long example. Never describe a guessed length as a maximum.

| Existing content | Useful cases |
| --- | --- |
| Titles, body, control labels | Long Chinese/Latin text, mixed scripts, a short value, translated labels |
| Paths, URLs, identifiers | A realistic unbroken value; check wrapping or intentional local scrolling |
| Optional metadata, lists | Missing optional value; zero, one, many items; check orphan separators and empty space |
| Counts, dates, numeric cells | Zero/one/large values, units, long formatting; preserve type and distinguish missing from zero |
| Images or attachments | Missing/broken source and available alternative text, only when such media exists |

Do not add counters, tables, images or empty-state logic solely for the test.
Mark absent surfaces not applicable. Missing required content is a data-contract
finding, not permission to fabricate replacement facts. Synthetic values must
not become report conclusions, provenance records or authoritative statistics.

## Execute and report

Use a bounded matrix: baseline plus the relevant cases, at the page's normal
width and a narrow width. Include enlarged text when it affects the page's
reader task. Run affected controls with the stressed values: switching panels,
opening details/dialogs, copying text and keyboard dismissal.

Check unintended page overflow, overflowing children, overlapping or clipped
controls, missing information and empty-state semantics. Intentional code/table
scroll containers are not automatically defects; record their accessibility.
Capture the selected states/viewports in one batch per version and inspect them
together. Browser assertions supplement visual inspection, not replace it.

Report case, field, viewport, observation and proposed fix. Separate:

- harness completion and content-preservation result;
- actual UI pass/fail findings, including failures found by a successful test;
- visual inspection versus inferred risks, and untested/not-applicable surfaces.

When only testing was requested, report defects without silently fixing the
delivery. Save reproducible fixtures, checks and screenshot references alongside
the artifact's test evidence, not inside its reader-facing flow. Existing Breach
telemetry can reference this evidence; do not add schema fields for this module.

## Source and local adaptation

Locally synthesized from Emil Kowalski's
[break-ui](https://github.com/emilkowalski/skills/blob/2d228630ba1446365f614a108cb8252f1feda202/skills/break-ui/SKILL.md)
and [catalog](https://github.com/emilkowalski/skills/blob/2d228630ba1446365f614a108cb8252f1feda202/skills/break-ui/CATALOG.md),
revision `2d228630ba1446365f614a108cb8252f1feda202`, reviewed 2026-10-22.
Retained: realistic boundary data, normal data entry points, inspect before fix.
Adapted: temporary standalone-page previews and delivery hashes instead of a
permanent demo/worst-case toggle; no upstream persona or orchestration imported.
