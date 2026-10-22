# General page variant comparison

Use only when the user requests alternative designs, multiple layouts, or a
comparison. Keep Breach responsible for layout, style provenance and delivery;
do not install or nest another prototype orchestrator.

## Make the comparison meaningful

Start with one reader task and a named axis: layout, density, navigation or
another explicitly requested distinction. Usually two or three alternatives
are enough. Name each direction by its actual treatment, not “A/B” or a vague
quality ranking. Changing only colors or wording is not a meaningful layout
comparison. State when each direction helps and what it costs; do not invent
performance scores or user-preference evidence.

Keep approved content, facts, values, links, provenance and available actions
the same across variants. Keep project design tokens and accessibility behavior
consistent unless the user explicitly wants to compare those. Content must not
be shortened, hidden permanently or replaced by synthetic figures to make a
variant look better. Content owners remain upstream.

For layout-only alternatives, prefer one semantic content tree with scoped
layout classes. For alternatives requiring different markup, derive both from
one content fixture and check content equality. Preserve logical reading and
focus order; visual reordering must not make keyboard navigation confusing.

## Isolate the preview

Create a separate comparison artifact or prototype route. Record the existing
deliverable's hash and leave it untouched. A standalone comparison should work
without a build step or an added framework. Keep variant styles scoped so they
cannot affect other pages.

Show one variant at full usable size at a time. Put a small, clearly labelled
picker outside the compared content, using native radios or accessible buttons.
Keyboard and touch must work; do not capture global keys used by inputs or
dialogs. Switching is immediate, with selected state exposed to assistive
technology. Keep shared interaction state where possible; when a remount is
necessary, explain what resets. The picker must not cover content or introduce
new scroll traps. Supply a readable default if scripts fail.

Do not put the picker into the existing delivery page. Selecting a preview
only changes the preview; it does not publish, persist a product decision,
overwrite a source artifact or remove other alternatives.

## Validate and hand off

- Verify every direction can be reached by pointer and keyboard at normal and
  narrow widths. Check selection state, readable text and overflow.
- Exercise the same important actions in every direction. Rapidly switch while
  preserving tab/disclosure state; keep dialog focus and reduced-motion behavior.
- Compare content values, links and actions against the common source, not just
  screenshots. Verify the original deliverable hash remains unchanged.
- Batch all relevant variant/viewport screenshots into one review per version.
  Use the General page content-stress reference when applicable, keeping its
  synthetic fixtures separate from both the source and comparison deliverable.
- Separate behavior and layout evidence from subjective preference. A screenshot
  or assertion cannot prove that users prefer a direction.

Deliver the comparison file and a short tradeoff table. Leave the choice to the
user. Only integrate a chosen direction when the user requests that action;
preserve content and provenance, and remove preview controls from the integrated
result. Retain comparison evidence unless cleanup is requested.

## Source and adaptation

Locally synthesized from Emil Kowalski's
[prototype](https://github.com/emilkowalski/skills/blob/2d228630ba1446365f614a108cb8252f1feda202/skills/prototype/SKILL.md)
at revision `2d228630ba1446365f614a108cb8252f1feda202`, reviewed 2026-10-22.
Retained: distinct axes, functioning variants, full-size instant switching,
explicit tradeoffs and user choice. Adapted: project-styled native picker,
shared factual content, source-hash preservation and retained evidence. No
fixed upstream picker markup, persona, automatic promotion or deletion imported.
