---
name: Cover
description: |
  Generate a customized DESIGN.md (design token specification) for a product
  or project. Reads the awesome-design-md reference library (71 DESIGN.md files
  from real products), synthesizes the best-matching references with the
  project's own content and style intent, and produces a tailored design spec.

  Trigger on: "visual design", "视觉设计", "DESIGN.md", "design spec",
  "设计规范", "产品视觉方案", "给我一个设计规范", "match design style",
  "参考 XX 风格做设计", "generate design tokens".
---

# Visual Design

Generate a DESIGN.md — a plain-text design token specification that AI coding
agents read to produce consistent, on-brand UI. Synthesize from the
awesome-design-md reference library, adapted to the user's project.

## Core Rule

Don't copy a reference DESIGN.md — adapt it. References provide the design
vocabulary (color families, type scales, spacing rhythms, component patterns);
your job is to remix them for the user's specific product, audience, and tone.

## Reference Library

```
~/.agents/repos/awesome-design-md/design-md/
```

71 DESIGN.md files from real products. The README.md in the repo root
categorizes them by industry. Always read the README first to understand
available categories and pick initial candidates.

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

Read the awesome-design-md README.md for the categorized index. Based on the
project's industry and tone, pick 2-4 reference DESIGN.md files to study.

Selection criteria:
- Same industry as the target project → strongest structural match
- Different industry but matching visual tone → useful for palette/typography
- Adjacent product type (e.g. B2B SaaS → other B2B tools) → UX pattern match

Read the selected DESIGN.md files in full to understand their design vocabulary.

### Step 3: Synthesize

Produce a DESIGN.md that blends:
- **From references**: color palette structure, type scale hierarchy, spacing
  rhythm, component-level tokens
- **From the project**: industry-appropriate conventions, audience expectations,
  unique brand elements

The synthesis should feel like a coherent design system, not a patchwork.
A single DESIGN.md should have a clear visual thesis — one dominant color
family, one type personality, one spacing philosophy.

### Step 4: Output

Generate the DESIGN.md with this structure:

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

After the DESIGN.md, list which references were studied and what was adapted
from each.

## Implementation Anti-Slop Rules

When the agent builds UI from this DESIGN.md, enforce these red lines. Each
rule comes from real AI-generated design patterns that users instantly
recognize as "AI-made."

### Typography
- No browser default fonts or Inter/Arial everywhere. Use distinctive fonts.
- Headlines must have presence — increase size, tighten tracking.
- Body text max width ~65ch. Increase line-height.
- Don't use only Regular (400) + Bold (700). Add Medium (500), SemiBold (600).
- Numbers in proportional font → use tabular-nums or monospace.
- All-caps subheaders everywhere → try lowercase italics or small-caps.
- Orphaned single words → `text-wrap: balance`.

### Color
- No pure `#000000` background. Use off-black, charcoal, or tinted dark.
- No oversaturated accent colors. Keep saturation below 80%.
- Pick one accent. Remove the rest.
- Don't mix warm and cool grays. Pick one gray family.
- No purple/blue "AI gradient" aesthetic. Single considered accent.
- No generic `box-shadow`. Tint shadows to match background hue.
- Flat design with zero texture → add subtle noise, grain, or micro-patterns.
- No perfectly even gradients. Break with radial, noise overlay, or mesh.
- One consistent light source for all shadows.
- Don't randomly drop a dark section into a light page (or vice versa).

### Layout
- No everything-centered symmetrical layouts. Break with offset or asymmetry.
- No three equal card columns as feature row. Zig-zag, asymmetric grid, or masonry.
- Use `min-height: 100dvh` not `height: 100vh`.
- Use CSS Grid over complex flexbox percentage math.
- Add a max-width container (~1200-1440px) so content doesn't stretch edge-to-edge.
- Don't force equal-height cards. Allow variable heights or use masonry.
- Vary border-radius: tighter on inner elements, softer on containers.
- Create overlap and depth with negative margins.
- Don't always use left sidebar for dashboards. Try top nav or floating command menu.
- Pin buttons to bottom of card groups so CTAs form a clean line.
- Align shared elements (titles, prices, buttons) across side-by-side cards.
- Optical alignment over mathematical center — 1-2px adjustments for visual feel.

### Interactivity
- Buttons must have hover states (background shift, scale, or translate).
- Add active/pressed feedback: `scale(0.98)` or `translateY(1px)`.
- Smooth transitions (200-300ms) on all interactive elements.
- Visible focus ring for keyboard navigation. Not optional.
- Skeleton loaders over generic spinners.
- Empty states are a design opportunity, not a blank page.
- Inline error messages on forms. Never `window.alert()`.
- Style active nav link differently from inactive.
- `scroll-behavior: smooth` on anchor clicks.
- Use `transform` + `opacity` for animations, never `top`/`left`/`width`/`height`.

### Content
- No "John Doe" or "Jane Smith" placeholder names.
- No fake round numbers (99.99%, $100.00). Use organic data (47.2%, $99.00).

## What Not To Do

- Don't copy a reference DESIGN.md wholesale — always adapt.
- Don't use more than 4 references — synthesis quality drops.
- Don't include implementation code (CSS, JSX, etc.) — DESIGN.md is a spec, not code.
- Don't prescribe exact component markup — describe the visual properties
  (border radius, shadow, padding) not the HTML structure.

## Canon 输出边界

读取共享契约：`/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md`。

- Generated DESIGN.md files are project artifacts. If a visual/design decision should persist across projects, record it in Canon `decisions/` or `patterns/` and reference the DESIGN.md path.
- Canon update-card path, when needed: `/media/yhr/2T/Canon/raw/update-cards/<date>-cover-<topic>.md`.
