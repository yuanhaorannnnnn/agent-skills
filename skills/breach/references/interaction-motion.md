# General page interaction and motion

Use interaction to help the reader act, follow a state change, or understand a
process. Reports default to immediate feedback and restrained transitions; do
not add page-wide entrances, scroll reveals, animated counters, or perpetual
motion just to make a page look active. A requested explanatory animation may
use more motion when it carries meaning. No chart or animation may invent data.

## Choose the smallest implementation

Keep the artifact's delivery format. Prefer semantic HTML, CSS transitions and
small local JavaScript. A standalone page does not need React, Sonner, or Motion
for a copy confirmation or dialog. Use an existing project library when present;
add a dependency only when a requested interaction warrants it.

Honor project motion tokens. If absent, local starting points are 100–160 ms
for press feedback and 150–240 ms for small transitions, typically ease-out
for entry. These are adjustable defaults, not acceptance thresholds. An anchored
popover should originate near its trigger; a centered dialog stays centered.

Prefer transform and opacity for motion, list transition properties explicitly,
and avoid animation-driven layout work when an equivalent transform works.
Do not assume CSS, filters, or GPU promotion guarantee smoothness. Add
will-change only for an observed issue, not globally. Content that naturally
changes height may reflow immediately; animate an indicator instead of clipping
text into a fixed-height box.

## Preserve control while state changes

| Control | Required behavior |
| --- | --- |
| Buttons and copy | Provide visible focus and press feedback. Confirm copy only after clipboard success; on failure keep selectable text and explain the fallback. Announce feedback without moving focus. |
| Tabs | Keep selection, visible panel and ARIA state synchronized; support arrow keys and Home/End with a roving tab stop. Frequent switching must not wait for an animation. |
| Disclosure | Prefer native details/summary. Keep expanded state and focus correct; do not leave hidden links in the tab order. |
| Dialog | Prefer native dialog where supported. Give it a name, sensible initial focus, Escape and close-button dismissal, focus containment and restoration. Handle backdrop dismissal only when the whole pointer action is outside the content. |

Rapid input retargets the current visual state. Do not disable a control until a
transition finishes, stack obsolete timers, or let a closing animation undo a
later reopen. Logical correctness must not depend on transitionend firing.
If a control is unavailable without JavaScript, hide it until initialized or
provide a working native fallback; keep the underlying reading content visible.

Respect prefers-reduced-motion, including changes while the page is open:
remove nonessential translation, scaling, smooth scrolling and animation while
preserving state, feedback and content. A preview switch may reduce motion
further, never override a system request for less motion. Hidden content must
not depend on an entrance animation to become readable.

Gate hover treatments by pointer capability. Keep a visible active/focus state
if removing native tap highlights. Preserve zoom, readable input sizes and
comfortable touch targets. Use dynamic or small viewport units and safe-area
insets only where the layout needs them; do not globally disable scrolling,
selection or overscroll to fix a local interaction.

## Verify the rendered interaction

Exercise the controls in a browser, not only through script evaluation:

- Click/tap each control and repeat or reverse it before a transition settles.
- Operate with keyboard; check focus visibility, tab order, dialog Escape and
  focus return, plus hidden content staying out of the focus order.
- Check reduced-motion, including a preference change with the page open.
- Check narrow width, long content and enlarged text for overflow or clipped
  controls. For clipboard, check success and denial separately.
- Capture relevant states and viewports together for one visual review per
  artifact version. Repeat only for an observed defect or an actual revision.

Report separately: functional browser results, inspected screenshots, and
device/performance evidence. Emulation is not real touch hardware, screenshots
do not prove motion quality, and a code review does not prove a frame budget.
If a needed browser check cannot run, state the gap instead of claiming it passed.

Record motion source/revision and local adaptations in the HTML provenance
comment; do not add implementation metadata to the reader-facing flow. Keep
browser checks beside the artifact. Use existing Breach telemetry fields;
do not invent new routing fields for this optional reference.

## Source and adaptation

Adapted on 2026-10-22 from Emil Kowalski's MIT-licensed skills at revision
`2d228630ba1446365f614a108cb8252f1feda202`:

- [animate](https://github.com/emilkowalski/skills/blob/2d228630ba1446365f614a108cb8252f1feda202/skills/animate/SKILL.md): purpose, timing, interruption and reduced motion.
- [animation-performance](https://github.com/emilkowalski/skills/blob/2d228630ba1446365f614a108cb8252f1feda202/skills/animation-performance/SKILL.md): rendering cost and evidence limits.
- [mobile-native](https://github.com/emilkowalski/skills/blob/2d228630ba1446365f614a108cb8252f1feda202/skills/mobile-native/SKILL.md): touch, viewport, zoom and real-device boundaries.

This is a locally authored synthesis, not a vendored copy or an upstream install.
Semantic controls, clipboard failure handling and General-page-only routing are
local integration requirements. Upstream aesthetic absolutes, persona/opening
messages, fixed review formats and agent orchestration are not imported.
