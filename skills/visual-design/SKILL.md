---
name: visual-design
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

## What Not To Do

- Don't copy a reference DESIGN.md wholesale — always adapt.
- Don't use more than 4 references — synthesis quality drops.
- Don't include implementation code (CSS, JSX, etc.) — DESIGN.md is a spec, not code.
- Don't prescribe exact component markup — describe the visual properties
  (border radius, shadow, padding) not the HTML structure.
