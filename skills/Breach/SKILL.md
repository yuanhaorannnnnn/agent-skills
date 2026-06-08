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
2. If not, read `~/.agents/repos/awesome-design-md/README.md`, choose 1-2
   matching DESIGN.md files, then read them.
3. Use only those DESIGN.md sources for `colors`, `typography`, `spacing`,
   radius, shadows, and component tone. html-effectiveness is layout-only.
4. Never write a DESIGN.md file. This lookup is read-only.

**Style gate**:

Before writing HTML, identify exact sources:

```text
layout_name: html-effectiveness catalog/page type name
layout_source: /absolute/path/to/html-effectiveness/example.html
style_sources:
- /absolute/path/to/DESIGN.md
tokens_used: colors, typography, spacing
```

If `style_sources` is empty, stop. `Style: Anthropic` without a DESIGN.md path
is invalid.

**Provenance footer**:

Every page must include a clean visible footer plus an HTML comment with exact paths:

```html
<!-- BREACH_PROVENANCE
layout_name="11-status-report"
layout_source="/abs/example.html"
style_name="Notion"
style_source="/abs/DESIGN.md"
-->
<footer>Layout: 11-status-report | Style: Notion</footer>
```

Do not show absolute paths in the visible footer. Exact paths live only in
`BREACH_PROVENANCE`.

## Output Location

HTML artifacts write to the **current repo working directory**, NOT to the
source material directory. Default output paths by context:

- Defect fix plans → `.proposal/repair/<bug-id>/index.html`
- Design proposals → `.proposal/<topic>/index.html`
- Research findings → `.research/<topic>/index.html`
- General artifacts → caller-specified path, defaulting to `.proposal/` if unspecified

When invoked by another skill (e.g., Repair), the caller provides the output
path; Breach accepts it and writes there. Never write HTML into
`/media/yhr/2T/yunxiao/` or other Phase 0 scraped data directories.

## Canon 输出边界

读取共享契约：`/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md`。

- HTML 页面是 artifact，仍写在调用者指定的 `.proposal/`、`.research/` 或其他 repo-local 路径。
- Breach 不主动复制 HTML 到 Canon；Canon 默认只记录 absolute path、HTTP URL、页面类型和它支持的 task/decision/incident。
- 如果页面承载长期结论（incident report、PR writeup、design summary），创建或更新 `/media/yhr/2T/Canon/raw/update-cards/<date>-breach-<topic>.md`，或让调用方 skill 负责 promotion。

## Agent-Specific

- **Claude Code**: use `frontend-design` for generation, passing the observed
  layout patterns and DESIGN.md tokens as constraints.
- **Codex / Pi**: generate HTML directly, using the example's layout patterns
  and the DESIGN.md tokens.
