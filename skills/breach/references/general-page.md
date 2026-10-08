# Breach general page

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

Two constraints, always applied:

**Layout — from html-effectiveness**:
1. Read `/media/yhr/2T/files/wiki/raw/assets/thariqs.github.io/html-effectiveness/catalog.md`.
2. Match the user's request to the closest page type.
3. Read the corresponding HTML example for its grid, component arrangement,
   and spatial patterns.

**Style — from DESIGN.md or awesome-design-md**:
1. If `DESIGN.md` exists in the target artifact's project root, use its tokens
   directly — skip the awesome-design-md lookup. Do not borrow another
   project's DESIGN.md unless the user or caller explicitly selects it.
2. If not, read `~/.agents/repos/awesome-design-md/README.md`, choose 1-2
   matching DESIGN.md files, then read them.
3. Use only those DESIGN.md sources for `colors`, `typography`, `spacing`,
   radius, shadows, and component tone. html-effectiveness is layout-only.
4. Never write a DESIGN.md file. This lookup is read-only.

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

**Style gate**:

Before writing HTML, identify exact sources:

```text
layout_name: html-effectiveness catalog/page type name
layout_source: /absolute/path/to/html-effectiveness/example.html
style_sources:
- /absolute/path/to/DESIGN.md
tokens_used: colors, typography, spacing
content_mode: selected mode, if the DESIGN.md defines content-modes
```

If `style_sources` is empty, stop. `Style: Anthropic` without a DESIGN.md path
is invalid.

**Provenance footer**:

Every page must include a clean visible footer plus an HTML comment with exact paths:

```html
<!-- BREACH_PROVENANCE
layout_name="11-status-report"
layout_source="/abs/example.html"
style_name="Field Notes Wiki"
style_source="/abs/DESIGN.md"
content_mode="research-explainer"
-->
<footer>Layout: 11-status-report | Style: Field Notes Wiki</footer>
```

Do not show absolute paths in the visible footer. Exact paths live only in
`BREACH_PROVENANCE`.
