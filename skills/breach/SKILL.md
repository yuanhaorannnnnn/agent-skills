---
name: breach
description: |
  Create a fast single-page HTML status page, diagram, slide-like page, PR/incident writeup, or digest of an email, issue, or chat thread. Trigger on "快速 HTML 页面", "画一个 HTML flowchart", "梳理这个讨论", or "digest this thread". Not for native docs, decks, sheets, or full websites.
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

## Minimal entry

Choose one artifact mode and read only its route:

- HTML status page, diagram, slide-like page, PR/incident page →
  [General page](references/general-page.md) for layout, project DESIGN.md tokens,
  optional chart gate, and provenance.
- Multi-party email, issue, PR, chat, or forum discussion digest →
  [Discussion digest](references/discussion-digest-mode.md) for schema and
  deterministic renderer.

For either mode, apply the writing discipline below before authoring new
technical narrative. A supplied approved text rendered faithfully needs no
re-authoring.

## Content Routing

Apply the content profile after choosing the artifact mode; it does not create
another renderer:

### Writing discipline

Before drafting or materially restructuring technical narrative in either mode,
invoke `paperwork`. It owns the content model, reader task,
information relationships, evidence calibration, and prose quality; Breach owns
HTML structure, visual tokens, rendering, and provenance. Follow that skill's
required calibration-corpus step before writing.

Apply this discipline when generating page copy, explanations, conclusions,
decision rationale, status narratives, or discussion-digest synthesis. If the
caller supplies approved prose and asks only for faithful HTML rendering, keep
the prose unchanged and skip re-authoring. Deterministic rendering never grants
Breach permission to invent or strengthen facts.

- **Default** — preserve the caller's normal level of detail and structure.
- **ELI5** — select when the caller marks `content_profile: eli5` or the user
  makes an explicit beginner-level request. Keep the General page renderer,
  but use one idea per section, short sentences, and concrete analogies
  labelled as analogies. Preserve evidence, qualifiers, uncertainty, and
  provenance; never invent a fact to make an explanation simpler.
- Do not force HTML for a plain request to "explain simply". If no HTML artifact
  is requested, answer inline; use `visualize` only when a visual materially
  improves understanding.

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
