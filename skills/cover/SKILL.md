---
name: cover
description: |
  Create or update a project-specific DESIGN.md with a distinctive art direction and visual tokens for pages, images, and video. Trigger on "DESIGN.md", "视觉设计", "设计规范", "design spec", or "参考 XX 风格做设计". Not for a one-off mockup or video production.
---

# Visual Design

Create or update a project-owned DESIGN.md: art direction, visual tokens, and
medium-specific expression rules. Renderers consume this contract; Cover does
not make pages, images, or films. Preserve existing project choices unless
the user requests a redesign.

## Core Rule

Don't copy a reference DESIGN.md — adapt it. References provide the design
vocabulary (color families, type scales, spacing rhythms, component patterns);
your job is to remix them for the user's specific product, audience, and tone.

## Art direction before tokens

State the project's visual idea and the concrete choices that make it recognizable:
composition, shape, color relationships, typography, material, and, when relevant,
motion and sound. Select a dominant direction rather than averaging references.
For image generation, follow the user's prompt; catalog style routing is not
mandatory unless requested. Serious data charts using `lieflat-charts` follow
its data, template and visual rules, not the surrounding artistic direction.
Warm paper, muted colors, rounded cards, and glossy gradients are choices, never
a universal safe default. Cold, monochrome, saturated, rough, or austere work can
be equally coherent. Legibility constrains use, not personality.

Before combining references or handing a direction to a renderer, read
[Cross-media design](references/cross-media-design.md), including reference
collaboration, conflict resolution and ownership. These rules also apply to HTML alone. For artist, artwork, or
launch-film references, read [Reference selection](references/visual-references.md).
A palette swap alone does not establish a new art direction. Each new HTML work
or film needs its own subject-led composition and signature choices, even when
its style family or project tokens are shared. Read the artifact-identity section of the
cross-media contract before handing a direction to a renderer.

## Reference Library

```
~/.agents/repos/awesome-design-md/design-md/
```

For product UI references, read the repo README first for the current index.
Artist portfolios, specific artworks, and official films can also supply
reference vocabulary; use actual inspected material and its provenance.

## Workflow

### Step 1: Understand the project

Ask the user (or infer from context):
- What is the product? (SaaS dashboard, CLI tool, developer platform, consumer app, etc.)
- Who is the audience? (developers, enterprise, consumers, designers, etc.)
- What is the desired visual tone? (warm/human, cold/technical, premium/luxury, playful, minimal, etc.)
- Any existing brand constraints? (logo, existing colors, company design system)

If the user gives a short description without these details, make reasonable
assumptions based on the product type and state them before generating.

### Step 2: Find reference matches

When a request names a style, supplies new visual references, or needs a direction
chosen, read [Style routing](references/style-routing.md). Use its catalog and
structured route to resolve explicit/project/evidence selection before synthesis.
Do not route from brand names or palette keywords alone. Preserve uncertainty
when observations are insufficient; adding references does not require a new skill.


Study 2–4 focused references selected for the project's task and artistic direction.
For UI references use the awesome-design-md index; for artworks/films use the
reference-selection guide. A style catalog is a discovery pool, not 29 inputs
to blend. Existing project DESIGN.md can be one reference during an update.

Select by the decision that needs evidence: expressive choices must fit the
work's thesis; structure and controls must fit the reader task. Industry similarity
can help find functional patterns but does not select the aesthetic. Use only
the relevant reference layers; do not force one source from each library.

Read selected specifications in full; inspect artworks directly and films at the
level needed for the claim. Record frame-only, sequence, audio, and creator-credit
evidence separately. Do not infer motion timing or sound from stills.

### Step 3: Synthesize

Produce a DESIGN.md around the resolved visual thesis. Derive tokens and
medium rules from it, adapting the useful choices from each inspected reference.
Preserve project constraints outside the requested change; record which defaults
are replaced and why. Do not average reference styles or let website tokens
overrule the selected art direction.

The synthesis should feel like a coherent design system, not a patchwork.
A single artifact should have a clear visual thesis. A project may define named
directions with explicit selection rules; resolve one direction per artifact.
Shared identity can survive different palettes and media through recurring
shape, composition, typography, material, or motion choices.

### Step 4: Output

Record the art direction (thesis, signature choices, scope, and avoided defaults)
before deriving tokens. Use the token structure below as a base; add medium rules
only for requested media, following the cross-media reference:

```yaml
---
version: alpha
name: <Project Name>
description: <One paragraph capturing the visual thesis — palette, type voice, spatial character>
---

colors:
  primary: "#hex"
  primary-active: "#hex"
  ink: "#hex"
  body: "#hex"
  muted: "#hex"
  hairline: "#hex"
  canvas: "#hex"
  surface-card: "#hex"
  surface-dark: "#hex"
  on-primary: "#hex"
  on-dark: "#hex"
  success: "#hex"
  warning: "#hex"
  error: "#hex"

typography:
  display-lg:
    fontFamily: "..."
    fontSize: 48px
    fontWeight: 400
    lineHeight: 1.1
  # ... through body-sm

spacing:
  unit: 4px
  # semantic spacing tokens

components:
  # key component patterns
```

Adapt the token set to what matters for the project. Don't include every
possible token — include what the AI agent needs to render the product's
core screens consistently.

After the DESIGN.md, list which references were studied and what was adapted from each.

Write evidence to `.design/evidence.json`:
```json
{
  "references_studied": ["vercel-DESIGN.md", "linear-DESIGN.md"],
  "adaptations": {"vercel-DESIGN.md": "dark color palette", "linear-DESIGN.md": "keyboard-first interaction"},
  "wholesale_copy": false
}
```

Run gate:
```bash
python3 <skill-dir>/scripts/synthesis_gate.py --design <path> --evidence .design/evidence.json
```
`pass` means structural checks passed, not that the style is distinctive or
visually accepted. Report structural validation and artistic review separately.
Inspect requested samples for recognizable choices, content fit, and fidelity
to the chosen direction; absent samples remain `not-run`. Do not generate
additional deliverables merely to satisfy a visual check.

## Optional Implementation Checks

Generating `DESIGN.md` does not require UI implementation advice. Only when the
user also asks to build or review the UI, read
[Implementation checks](references/implementation-anti-slop.md). It checks
functional correctness and fidelity, without adding aesthetic defaults.

## What Not To Do

- Don't copy a reference DESIGN.md wholesale — always adapt.
- Keep the synthesis to 2–4 studied references; the discovery library can be larger.
- Don't include implementation code (CSS, JSX, etc.) — DESIGN.md is a spec, not code.
- Don't prescribe exact component markup — describe the visual properties
  (border radius, shadow, padding) not the HTML structure.

## Canon 输出边界

读取共享契约：`/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md`。

- Generated DESIGN.md files are project artifacts. If a visual/design decision should persist across projects, record it in Canon `decisions/` or `patterns/` and reference the DESIGN.md path.
- Canon update-card path, when needed: `/media/yhr/2T/Canon/raw/update-cards/<date>-cover-<topic>.md`.
