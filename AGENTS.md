# Cross-Agent Memory & Operational Guidelines

This document serves as the shared "Long-Term Memory" and operational rulebook across all coding agents (Claude Code, Codex, Pi). It consolidates user preferences, style guides, and critical constraints into a single, authoritative instruction set.

---

## 1. Language Preference
- **Response Language:** You **MUST** provide all responses, explanations, reasoning, and documentation content in **Chinese (Simplified)** unless explicitly requested otherwise by the user.
- **Term Preservation:** Technical terms, variable names, function names, file paths, and code snippets **MUST** remain in their original **English** form to ensure technical accuracy and avoid translation ambiguity.

---

## 2. Documentation Standards

When creating or updating technical documentation:

- **Preferred**: structured Markdown with clear headings, code navigation tables, and inline diagrams where they add clarity.
- **Adapt to medium**: Markdown for repo docs; HTML artifacts for visual reports, slide decks, or interactive explainers.
- **Tone**: Objective and evidence-based, grounded in actual codebase analysis. Avoid vague descriptions.

## 3. Diagram Standards

**Default to ASCII art** for inline diagrams in Markdown documentation — it's portable, version-control friendly, and has zero rendering dependencies. Use SVG, Mermaid, or HTML-based diagrams when the medium benefits from richer visuals (web artifacts, slide decks, reports).

### ASCII Art Rules (when applicable)
1. **English Only**: All text inside ASCII diagrams MUST be in English — CJK characters misalign in monospace. Use English labels, describe in surrounding Chinese prose.
2. **Box-Drawing Characters**: `┌ ┐ └ ┘ ─ │ ├ ┤ ┬ ┴ ┼` for structure; `→ ← ↑ ↓ ▼ ▲ ► ◄` for arrows.
3. **Consistent Widths**: Pad box content to equal width within a column.
4. **Hierarchy**: Indent 2-4 spaces for trees; use `├──` / `└──` for branches.
5. **Wrap in Code Blocks**: Always use triple-backtick fenced code blocks.

### Example
```
┌─────────────────┐     ┌──────────────────┐
│  Input Data      │────>│  Processing       │
│  (Source A)      │     │  Module           │
└────────┬────────┘     └────────┬─────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌──────────────────┐
│  Intermediate   │     │  Output           │
│  Cache          │────>│  Result           │
└─────────────────┘     └──────────────────┘
```

## 4. Visual Output — Two-Path System

Two distinct scenarios for visual output. Choose the correct path before starting.

### Path A: Product-Level Visual Design

When the user is building a **complete product** (app, website, platform, SaaS tool, portfolio, etc.) and needs a coherent visual identity:

1. Trigger `product-look` to generate a `DESIGN.md` with design tokens (colors, typography, spacing).
2. Save `DESIGN.md` to the project root.
3. When the user later needs specific pages, use `frontend-design` (if available — Claude Code) or generate HTML directly (Codex/Pi) with DESIGN.md tokens as constraints.

### Path B: Page-Level Visual Expression

When the user needs a **single page or artifact** for daily dev work (status report, slide deck, flowchart, diagram, PR writeup, incident report, etc.):

1. Read `/media/yhr/2T/files/wiki/raw/assets/thariqs.github.io/html-effectiveness/catalog.md`.
2. Match the user's requested page type to the closest entry in the catalog (9 categories, 20 examples).
3. Read the corresponding example file(s) to study their layout structure and component patterns.
4. Generate the page:
   - **Claude Code**: use `frontend-design` to generate, adapting observed patterns.
   - **Codex / Pi**: generate HTML directly, using the example's CSS variables, typography, and component patterns as reference.

### DESIGN.md Priority Rule

When a `DESIGN.md` exists in the project root, treat its tokens as non-negotiable constraints:
- **colors**: use the exact hex values from `DESIGN.md`
- **typography**: use the exact font families, sizes, and weights from `DESIGN.md`
- **spacing**: use the spacing unit and scale from `DESIGN.md`

Within these constraints, the agent still exercises creative freedom — layout composition, animation, background details, and decorative elements remain its domain.

## 5. Operational Mandates
- **Verification:** Always verify file paths and content existence before operating.
- **Safety:** Do not revert changes unless explicitly asked.
- **Completeness:** When generating diagrams, ensure no logic branches are left "hanging" (unconnected).
