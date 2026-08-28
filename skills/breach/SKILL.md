---
name: breach
description: |
  Generate fast single-page HTML artifacts for daily development communication:
  status pages, HTML slide-like pages, flowcharts, PR writeups, incident pages,
  and structured discussion digests. Use the discussion-digest mode for email
  threads, GitHub issues/PRs, chat logs, and forum discussions when the user asks
  "梳理这个讨论", "这条线程结论是什么", "理一下参与人立场",
  "digest this thread", or "summarize this email chain". Use the general page
  mode for "quick HTML page", "快速 HTML 页面", "做个 HTML status page",
  "画一个 HTML flowchart", "做个 HTML slide page", "生成报告页面",
  "visualize this as a page", or "把这个做成 HTML". When the task already
  calls for a general page, support an optional ELI5 content profile for
  explicit requests such as "ELI5", "像给小孩解释", or "给新手讲". Not for
  native documents, native slide decks, spreadsheets, or full product visual
  design.
---

# Quick Page

Fast, single-page HTML artifacts for daily dev communication.

## Output Boundary

breach owns HTML and deterministic discussion-digest rendering only.

- Native document, presentation, or spreadsheet requested → use the requested
  OpenAI Template or native artifact capability.
- HTML page, HTML slide-like page, or discussion digest requested → use breach.
- Another workflow may define content and evidence first, then call breach only
  for HTML presentation.

## Core Rule

Speed first, polish follows. A good-enough page in 30 seconds beats a perfect
page in 5 minutes.

Choose one mode:

- **General page** — use html-effectiveness for layout and DESIGN.md sources for visual tokens.
- **Discussion digest** — use the bundled schema, renderer, and template. Do not run the generic layout/style selection because this mode is deterministic.

## Content Routing

Apply the content profile after choosing the artifact mode; it does not create
another renderer:

- **Default** — preserve the caller's normal level of detail and structure.
- **ELI5** — select when the caller marks `content_profile: eli5` or the user
  makes an explicit beginner-level request. Keep the General page renderer,
  but use one idea per section, short sentences, and concrete analogies
  labelled as analogies. Preserve evidence, qualifiers, uncertainty, and
  provenance; never invent a fact to make an explanation simpler.
- Do not force HTML for a plain request to "explain simply". If no HTML artifact
  is requested, answer inline; use `visualize` only when a visual materially
  improves understanding.

## General Page Mode

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

When invoked by another skill (e.g., repair), the caller provides the output
path; breach accepts it and writes there. Never write HTML into
`/media/yhr/2T/yunxiao/` or other Phase 0 scraped data directories.

## Discussion Digest Mode

Use this mode for multi-party threads where the useful output is who argued what, how positions changed, what was decided, and what remains open.

1. Acquire the source with the connected GitHub/Gmail capability, a user-provided transcript, or the available web fetcher.
2. Read `references/discussion-digest-schema.md` before analysis.
3. Produce schema-compliant JSON. Keep the timeline at 30 entries or fewer, mark at most 8 key events, include at least one decision record, and keep `unresolved` non-empty.
4. Write the auditable intermediate artifact to `raw/discussions/<slug>.json` unless the caller specifies another path.
5. Render deterministically:

```bash
python3 <skill-dir>/scripts/render_discussion.py \
  raw/discussions/<slug>.json -o queries/<slug>.html
```

The bundled `assets/discussion-digest.html` owns layout and style for this mode. The renderer adds breach provenance. Do not rewrite the HTML by hand unless the template itself needs repair.

## Canon 输出边界

读取共享契约：`/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md`。

- HTML 页面是 artifact，仍写在调用者指定的 `.proposal/`、`.research/`、`queries/` 或其他 repo-local 路径。
- Discussion digest 的 JSON 是可审计中间产物；决议、争议和 action items 可提升到 Canon `decisions/`、`tasks/`、`patterns/` 或 update-card。
- breach 不主动复制 HTML 到 Canon；Canon 默认只记录 absolute path、HTTP URL、页面类型和它支持的 task/decision/incident。
- 如果页面承载长期结论，创建或更新 `/media/yhr/2T/Canon/raw/update-cards/<date>-breach-<topic>.md`，或让调用方 skill 负责 promotion。

## Agent-Specific

- **Claude Code**: use `frontend-design` for generation, passing the observed
  layout patterns and DESIGN.md tokens as constraints.
- **Codex / Pi**: generate HTML directly, using the example's layout patterns
  and the DESIGN.md tokens.
