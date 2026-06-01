---
name: Breach
description: |
  Fast, single-page HTML artifact for daily dev communication — status reports,
  slide decks, flowcharts, diagrams, PR writeups, incident reports, and more.
  Not for full product visual design (use `product-look` for that).

  Every time this skill triggers, first read the html-effectiveness catalog to
  match the page type to the closest layout reference, then generate.

  Trigger on: "quick page", "快速页面", "做一个页面", "生成一个",
  "make a page", "create an artifact", "做个 status report",
  "画一个 flowchart", "做个 slide deck", "生成报告页面",
  "visualize this as a page", "把这个做成 HTML".
---

# Quick Page

Fast, single-page HTML artifacts for daily dev communication.

## Core Rule

Speed first, polish follows. A good-enough page in 30 seconds beats a perfect
page in 5 minutes. Two reference libraries feed every generation: layout
structure from html-effectiveness, visual tokens from awesome-design-md.

## Before You Generate

Two constraints, always applied:

**Layout — from html-effectiveness**:
1. Read `/media/yhr/2T/files/wiki/raw/assets/thariqs.github.io/html-effectiveness/catalog.md`.
2. Match the user's request to the closest page type.
3. Read the corresponding HTML example for its grid, component arrangement,
   and spatial patterns.

**Style — from DESIGN.md or awesome-design-md**:
1. If `DESIGN.md` exists in the project root, use its tokens directly — skip
   the awesome-design-md lookup.
2. If not, read `~/.agents/repos/awesome-design-md/README.md` for the
   categorized index. Match the page's tone and audience to 1-2 closest
   DESIGN.md references. Read them and use their `colors`, `typography`, and
   `spacing` tokens.
3. **Never write a DESIGN.md file to disk.** The style lookup is always
   read-only. Only `product-look` creates permanent DESIGN.md files.

Generate with layout from html-effectiveness, tokens from the matched style.

## Agent-Specific

- **Claude Code**: use `frontend-design` for generation, passing the observed
  layout patterns and DESIGN.md tokens as constraints.
- **Codex / Pi**: generate HTML directly, using the example's layout patterns
  and the DESIGN.md tokens.
