# Breach general page

## Requested variant comparison

When the user explicitly asks to compare design alternatives, see
[Variant comparison](variant-comparison.md). Keep the content and project tokens
constant unless those are the requested comparison axis. This optional General
page route does not make ordinary page generation produce multiple versions,
and does not apply to Discussion digest or Archive.

## Content stress checks

When the user requests content stress testing, or the page has variable-length
content, optional fields or data-driven collections that could break its layout,
read [Content stress checks](content-stress.md). Test an isolated preview before
delivery, preserve real content, and report findings separately from harness
success. This route belongs only to General page, not Discussion digest or Archive.

## Interaction and motion

After resolving layout and style, decide whether the reader needs controls or
motion. For tabs, disclosures, copy feedback, dialogs, touch interactions, or
explicitly requested animation, read [Interaction and motion](interaction-motion.md)
before implementation. Static reading pages need no motion layer. Apply this
reference only in General page; Discussion digest and Archive keep their own
template contracts. Interaction rules supplement, not replace, project tokens.

## Optional Chart Renderer

In General page mode, `lieflat-charts` may render a chart module inside the
page. Breach still owns page integration and chart placement;
`paperwork` owns the surrounding narrative.

Use it only when all are true:

- the input contains real quantitative data or an honest relationship graph;
- a chart carries an independent conclusion better than prose, cards, or a table;
- the visual encoding does not require invented scores, weights, or benchmarks;
- the artifact's use is compatible with the renderer's license.

Keep this route small: normally 1–3 charts, each with a distinct conclusion.
Do not chart decorative KPIs, qualitative comparisons, or every available
column. If `lieflat-charts` is unavailable, continue with native HTML/CSS/SVG;
do not install a dependency implicitly. Preserve both Breach page provenance
and the chart template/license provenance.


## Optional Interactive Illustration

In General page mode, `hairline-create` may supply an SVG line illustration
for an empty state, a feature card, or one concrete concept metaphor. Use it
when the object and pointer response clarify that state or idea; omit it when
prose, a table, or a diagram already communicates the point. This route does
not apply to the deterministic Discussion digest mode.

Breach owns page layout, narrative, labels and actions. Hairline owns the
figure, its engine and its checks. Invoke the installed upstream skill and
follow its build, validator and visual checks; keep its kernel and bench
unchanged. Generate in the caller's artifact directory. The managed upstream
source and pinned revision live in agent-platform's
`migration/upstream-manifest.yaml`; do not copy that skill into agent-skills.

Keep the validated standalone HTML as the source artifact. When useful inside
the page, embed it in an isolated iframe with a descriptive `title` (`srcdoc`
for a single-file deliverable, a relative sibling path for a file bundle).
Keep the business heading and action in the parent page. Check the final embed
at its actual width and theme: the plate must match its background, and the
rest pose must communicate without pointer input. For PDF or email output,
use an inspected static rest image plus the same heading/action and a link to
the interactive artifact; preserve accessible text outside the image.

Do not use Hairline for measured charts, workflow topology, status truth, or
business controls. If unavailable, continue with native HTML/CSS/SVG; do not
install implicitly. Record the figure source, revision and validation evidence
in page provenance. Passing the text validator alone is not visual acceptance.


## General Page Mode

Read [the shared reference collaboration rules](../../cover/references/cross-media-design.md)
before resolving a new page's design. Breach owns the artifact brief and final
implementation; a new project DESIGN.md is not a prerequisite.

1. Read the target project's DESIGN.md if present. Separate fixed constraints
   from defaults/legacy tokens and resolve the work-specific visual idea. Keep
   unrelated projects' specifications out unless explicitly selected as references.
2. When reading structure is unresolved, consult
   `/media/yhr/2T/files/wiki/raw/assets/thariqs.github.io/html-effectiveness/catalog.md`
   and a relevant HTML example. Borrow information grouping and spatial patterns,
   then adapt them to the content and direction. Existing or straightforward
   structures need no lookup; label an original layout honestly.
3. When typography, controls or components need reference, consult
   `~/.agents/repos/awesome-design-md/README.md` and read only relevant DESIGN.md
   files. Skip this lookup when the project/brief already resolves those choices.
4. Derive the artifact's concrete tokens from its direction and inherited
   constraints. Exact source paths/URLs support reference choices; original
   choices carry a brief rationale. Scoped overrides can change default colors,
   fonts and component appearance without editing the project's DESIGN.md.
   Breach does not write DESIGN.md; use Cover when a reusable spec is requested.

**Content mode — when the selected DESIGN.md defines `content-modes`**:
1. Choose the mode from the artifact's reader task and evidence type, not from
   its filename or a keyword alone. For Field Notes Wiki, use `wiki-note` for
   routine notes, `research-explainer` for technical learning pages and design
   explanations, `release-or-concept-feature` for an explicitly editorial
   feature, and `status-or-benchmark` for measurements and acceptance reports.
2. Apply that mode's treatment only within the requested HTML artifact. A
   matching mode does not invoke breach, create a hero illustration, rewrite
   approved prose, or restyle other deliverables.
3. If the page contains both an editorial opening and evidence-heavy sections,
   the hero may use the editorial layer; charts, tables, code, screenshots, and
   status colors remain analytical. User/caller brand constraints override the
   project default.
4. Record the selected mode in the provenance comment as `content_mode`; the
   visible footer still needs only layout and style.

**Resolved brief and provenance**:

Before implementation, retain the visual idea, concrete signature choices,
inherited constraints, scoped token overrides and references actually used in
the existing brief or conversation. A catalog ID, brand name or palette alone
is insufficient. An original direction is valid without a DESIGN.md source;
record it as original rather than inventing a source path.

Every page keeps a clean visible footer and a `BREACH_PROVENANCE` HTML comment.
The comment carries exact reference paths/URLs and their roles, or identifies
original decisions. Retain existing provenance keys for compatibility; add
`art_direction`, `medium`, `artifact_idea`, `reference_roles` and `scoped_overrides`
when relevant. `layout_source`/`style_source` may be `original` when no external
source supplies that choice; explain that choice in the brief. Do not manufacture
a route receipt when the structured router was not used.

```html
<!-- BREACH_PROVENANCE
layout_name="original comparison layout"
layout_source="original"
style_name="work-specific geometric study"
style_source="/abs/DESIGN.md"
art_direction="precisionism"
medium="page"
artifact_idea="Organize prediction, observation and residuals as three linked test bays."
reference_roles="/abs/DESIGN.md: inherited typography; geometry/composition: original translation"
scoped_overrides="page only: legacy rounded panels replaced by hard-edged bays"
-->
<footer>Layout: comparison | Style: geometric study</footer>
```

Use actual decisions, not these illustrative values. Keep absolute paths and
implementation details in the comment, outside the visible footer. When no
catalog family applies, use a descriptive direction rather than a fictitious ID.
For telemetry, use `style=none` when no DESIGN source was used; the resolved
original direction remains in provenance, so `none` does not mean unstyled.

## Cross-media project contracts

When DESIGN.md has `art-direction` or `medium-rules`, consume the rules for the
requested medium only. Record the resolved direction as `art_direction` and the
medium as `medium` in BREACH_PROVENANCE. Existing specifications without these
fields remain valid as inherited constraints; new works still need an
artifact-specific direction.

Apply the shared conflict-resolution rules: explicit artifact direction can
select a new direction outside the project catalog. Otherwise use the project's
selection rule, treating `per-artifact` as requiring a fresh choice. Record any
scoped override; do not silently mute its colors or change the project DESIGN.md. Never import the Wiki's warm-paper style into an
unrelated project. Content modes choose treatment and density, not a mandatory
palette. Fonts, negative space, hard edges, saturation, and texture may express
personality while evidence remains legible and semantically accurate.

For an HTML storyboard/review page, preserve shot order, timecodes, captions,
audio intentions and validation status supplied by the video owner. Keep page
navigation and explanatory labels outside the frames. A storyboard can describe
motion; it cannot prove an exported film, soundtrack, or timing has been tested.
Discussion digest and Archive retain their dedicated template contracts.

Review technical usability and artistic fidelity separately. Inspect the actual
render for the chosen signature choices and topic-specific composition. Passing
layout, overflow, or accessibility checks does not establish a distinctive style.
If the requested personality disappeared, revise the relevant composition,
typography, imagery, or motion rather than merely swapping accent colors.


### Shared style routing when a direction needs selection

Layout is selected for the reader task and adapted to the resolved direction. For an explicit new style,
reference-led direction, or unresolved alternatives, read
[Cover's style-routing contract](../../cover/references/style-routing.md) and
use `<skills-root>/cover/scripts/style_route.py` when Cover is installed. Pass
observations grounded in inspected material; record the selected ID and receipt
path in the artifact provenance. `proposed`, `ambiguous`, `needs_observation`, `needs_context`,
`needs_style_definition`, and `conflict` are not completed selections, even when
the script exits 0. Resolve them as the contract specifies before applying style. For a selected contextual/umbrella family, honor
`reference_refinement_required` and its refinement note before production.

A selected direction supplements the project's tokens through an explicitly
scoped artifact brief; it does not authorize Breach to edit DESIGN.md. Existing
project pages still use their specification directly without invoking the router
or searching references. If the optional router is unavailable, preserve the
explicit/project direction and disclose that structured matching was not run;
do not invent a registered style. Archive/digest do not enter this route.


### Artifact identity before implementation

For every new General page, resolve the work-specific visual idea and signature
choices described in [the cross-media contract](../../cover/references/cross-media-design.md).
Record them in the existing brief or conversation and carry the direction into
composition, typography, imagery and interaction. Selecting a catalog family or
project default alone is not design completion. Comparison with the nearest
available prior work should expose intentional content-led differences; a color
swap is not enough. No additional approval form is required.

Validate the rendered result against those choices. Generic layout examples are
structural references, not skins to copy. Functional checks may fix an unreadable
caption or broken control but may not silently replace saturation, symmetry,
font choices or dramatic scale with a universal safe aesthetic. Dedicated
Archive/digest requests still preserve their requested template identity;
redesigning those templates requires that scope rather than a silent restyle.
