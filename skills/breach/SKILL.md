---
name: breach
description: |
  General HTML presentation layer for fast single-page designs, test reports, status pages, diagrams, or slide-like pages, plus dedicated structured discussion-digest and archive modes. Trigger on HTML artifact requests, explicit structured discussion digests ("digest this thread"), `$breach --archive`, requests to render an existing dossier material package, or dossier retrieval handoffs for default archive display; ordinary reading, explanation, or text summaries do not automatically request HTML. Content workflows such as conops remain the content owners. Not for native docs, decks, sheets, full websites, or rendered video files.
---

# Quick Page

Fast, single-page HTML artifacts for daily dev communication.

## Output Boundary

Breach is the general HTML presentation layer, not a mutually exclusive topic
category alongside `conops`. Designs, test reports, and discussions can all use
HTML. The caller owns the task's content contract and facts; `paperwork` owns
technical writing discipline when authoring is needed.

The dedicated Discussion digest mode additionally organizes an explicitly
requested structured digest using its bundled schema, then renders deterministic
HTML. This request can default to HTML without a separate format instruction;
ordinary discussion reading, explanation, or text summaries do not enter this
mode or automatically produce HTML.

- Technical design, Markdown → `conops`.
- Technical design, HTML → `conops` content + Breach General page rendering.
- Test report, HTML → caller's report content + Breach General page rendering;
  HTML alone does not invoke `conops`.

- Native document, presentation, or spreadsheet requested → use the requested
  OpenAI Template or native artifact capability.
- HTML page, HTML slide-like page, or discussion digest requested → use breach.
- Another workflow may define content and evidence first, then call breach only
  for HTML presentation. Approved prose need not be a persisted Markdown file.
- For `conops` output `html` or `both`, use General page mode and preserve its
  14-section content contract. `html` requires no Markdown artifact; `both`
  derives HTML from the Markdown maintenance source. Conops validates the final
  HTML with its own quality gate; Breach rendering and visual checks still apply.

A requested HTML storyboard, video review page, or player belongs to General
page. A requested rendered film belongs to an available video-production
capability; pass the project DESIGN.md, selected direction, content, and delivery
requirements. If none is available, identify the gap without substituting an
HTML animation for a video. Do not invoke a hypothetical skill.

## Core Rule

Deliver efficiently while preserving the chosen art direction. A generic page
that erases the requested style is incomplete even if it renders correctly.

Choose one mode:

- **General page** — resolve the artifact direction and inherited constraints, then use website and layout references only where needed under the shared collaboration rules; load the interaction reference for controls or requested motion.
- **Discussion digest** — use the bundled schema and renderer; resolve an artistic direction and use an artifact-specific template when appropriate.
- **Archive (`--archive`)** — render only a registered, dossier-gate-validated standard package with the bundled archive renderer/template and its reference-backed `assets/archive-DESIGN.md`. Material acquisition and conclusions remain upstream; no automatic dossier creation.

For a General page or Discussion digest with an explicitly requested new artistic style, run the
existing Cover style router before rendering, inspect its status and record the
actual receipt in provenance, as specified in General page. Do not infer that
reading the reference or naming a style is equivalent to running it. If the
router is unavailable, follow the documented fallback and disclose it. A
previously routed unchanged direction can reuse its existing receipt.

## Minimal entry

Choose one artifact mode and read only its route:

- `$breach --archive [manifest.json]` or render an existing dossier material package →
  [Archive](references/archive-mode.md). Require the dossier manifest and its identity catalog; the renderer runs dossier gate before rendering. An omitted input must resolve to one explicit registered package in context; otherwise ask for it. Reject raw documents or ad-hoc manifests; never standardize them inside breach. “调取XX的档案” first belongs to dossier for read-only lookup; dossier then calls Archive by default with the registered manifest, catalog and a separate output path. Breach does not perform the lookup or modify the source dossier.

- HTML status page, diagram, slide-like page, PR/incident page →
  [General page](references/general-page.md) for reference collaboration, scoped
  tokens, optional chart gate, and provenance.
- Multi-party email, issue, PR, chat, or forum discussion digest →
  [Discussion digest](references/discussion-digest-mode.md) for schema and
  deterministic renderer.

For each mode, apply the writing discipline below before authoring new
technical narrative. A supplied approved text rendered faithfully needs no
re-authoring.

## Content Routing

Apply the content profile after choosing the artifact mode; it does not create
another renderer:

### Writing discipline

Before drafting or materially restructuring technical narrative in the selected mode,
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
- Archive → `.proposal/archive/<dossier-id>/index.html`, outside the read-only source package.
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
  artifact brief, inherited constraints, scoped overrides and relevant layout patterns.
- **Codex / Pi**: generate HTML directly from the same resolved artifact brief
  and scoped tokens; references inform rather than replace its direction.

## Routing telemetry

At entry, retain the trigger category and entry form. After the final local
verdict, emit **one** event following
[the shared routing contract](/home/yhr/.agents/repos/agent-skills/references/skill-telemetry.md).
Use `route=general-page|discussion-digest|archive|native-handoff|inline-answer|unresolved`.
A route is the branch actually entered, even if it later fails. Record
`content-profile=default|eli5`, `prose=author|faithful`, and the selected style
source category. For General page, also record chart/Hairline decisions after
resolving availability and integration; for digest, record the actual style
source and use `charts=omit`, `hairline=omit`. Archive uses `style=archive-template`, `prose=faithful`, and the same omitted chart/illustration decisions; record actual render/visual checks. It preserves existing relationship views, not new analytical content.

Record actual step states for `paperwork`, `layout`, `style`, `render`, `charts`,
`hairline`, `visual-check`. `pass` requires the relevant completed work or check;
selection alone is `pending`. Faithful prose → `paperwork=skipped`; digest →
`layout` and `style` reflect the actual selected template and style work.
Modules omitted by decision → `skipped`; unavailable requested modules with a
working native fallback → module `skipped`, rendered fallback verified separately.
Stop before rendering → `render=pending`, never `pass`.

Only set `expected-route` when user/caller intent unambiguously requires that
branch. Never infer expectation from your own selected route. Attach generated
HTML/JSON and available check references via `artifact`/`gate`. Native/inline
handoff emits `skipped` for Breach artifact production, with the actual route.
Telemetry failure remains a warning; nested skills emit their own events.
