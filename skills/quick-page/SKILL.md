---
name: quick-page
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
page in 5 minutes. The html-effectiveness catalog provides the layout reference —
adapt it, don't redesign from scratch.

## Before You Generate

1. Read `/media/yhr/2T/files/wiki/raw/assets/thariqs.github.io/html-effectiveness/catalog.md`.
2. Match the user's request to the closest page type in the catalog.
3. Read the corresponding HTML example to study: layout grid, CSS variables,
   color palette, typography, and component patterns.
4. Generate the page, adapting those patterns to the user's content.

## Agent-Specific

- **Claude Code**: use `frontend-design` for generation, passing the observed
  layout patterns as reference.
- **Codex / Pi**: generate HTML directly, using the example's CSS variables,
  typography, and component patterns.
