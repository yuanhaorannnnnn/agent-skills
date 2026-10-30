# Style discovery and routing

Use when selecting a direction from references, adding a new reference, or
choosing between named styles. This is the style axis; artifact type and reader
task determine layout/story structure, which is then adapted to the direction.
[Reference collaboration](cross-media-design.md) defines how art references,
website specifications and layout examples combine; none is mandatory for every work. A release film, a
method explainer and an archive tour may share a style without sharing a script.

## Sources of truth

- `style-catalog.json`: stable style IDs, aliases, signature features, distinction
  notes and medium treatments. It is an evolving working design vocabulary,
  not a complete art-history taxonomy. Historical-inspired directions and
  contemporary treatments are labelled separately.
- Wiki raw collection manifest: external reference identity, archives and
  optional `style_observations`. References may be unclassified or span styles.
- Project DESIGN.md / artifact brief: actual chosen direction and scoped
  overrides. Selection is not written back into a source work's identity.
- `.design/style-route.json`: save the router's output when routing is used,
  then record the agent's content-fit decision and selected ID in the brief.
  `proposed` is not `selected`; keep the original receipt unchanged.

`selected` resolves the style family only. Every result carries
`selection_scope: style-family` and `artifact_direction_required: true`. Before
production, derive this work’s own visual idea and signature choices using the
cross-media contract; an existing project default does not skip that step.

The catalog covers all 29 source-video labels. Material collage, generative fields and expressive typography are techniques, not catalogued artistic styles.
Each historical entry links institutional sources and distinguishes historical
scope from proposed page/image/video treatments. See
[the 29-label guide](art-style-guide.md) for the mapping and important confusions.
Definition coverage is complete; visual-classifier accuracy and all rendered
styles have not been benchmarked.

## Observe before matching

The agent inspects the image/film and writes observable features with source,
segment scope, locator and a concrete note. A film with mixed shots gets
separate scopes; never classify its whole identity from one showcase shot.
Frames support visual composition; sequence inspection supports motion;
audio inspection supports sound. Artist/brand names, topic words, popularity,
and color alone do not supply signature evidence.

The script checks and matches those observations. It does not inspect pixels,
infer authorship or perform learned visual classification. The agent must check
the match against the actual material and the catalog's distinction note.

```json
{
  "medium": "video",
  "observations": [
    {"feature":"text-as-image", "source":"/absolute/frame.png",
     "scope":"opening", "locator":"00:02", "level":"frames",
     "note":"Large words occupy the main visual field."},
    {"feature":"scale-led-hierarchy", "source":"/absolute/frame.png",
     "scope":"opening", "locator":"00:02", "level":"frames",
     "note":"Word size and placement establish the reading order."}
  ]
}
```

Examples are illustrative input shapes, not observations already made. For
catalogued references, pass `reference_ids` with `--references <manifest.json>`
instead of copying observations. Each reference may contain `style_observations`
in the same shape, with `source` matching that record’s source_url, archive or
contact_sheet; existing manifests without them remain valid and unclassified.

## Selection order and outcomes

1. `explicit_style`: exact registered ID or alias. Select it even if a project
   default differs, preserving the override scope. Unknown names return
   `needs_style_definition`; excluded or unsupported directions return
   `conflict`. Do not silently substitute a familiar style.
2. `project`: `{ "style_id": "field-notes", "design": "/abs/DESIGN.md" }`.
   Read the file first and use its actual selected/default direction. Existing
   styles need not be in the shared catalog. If DESIGN uses
   `art-direction.selection-mode: per-artifact` without a chosen ID, it has no
   default family: do not pass its legacy direction as `project.style_id`.
   Resolve the work through explicit direction or inspected references instead.
   The script checks path presence,
   not whether the agent interpreted that file correctly.
3. Observed features: a candidate needs all its signatures from the same source
   and segment scope, covering multiple dimensions. One match returns
   `proposed`; several return `ambiguous`; none returns `needs_observation`.
   Entries with `auto_match: false` are contextual or umbrella labels: matching
   appearances go to `context_candidates`, never visual candidates. If only
   those remain, return `needs_context` and inspect the named work, author or
   historical source. Explicit selection remains supported, with
   `reference_refinement_required: true`; refine the branch in the artifact
   brief before production. No mandatory approval round is added.
   Matching is exact and explainable, with no invented confidence percentage.

`exclude_styles` is an artifact-specific constraint. Do not translate rejection
of one sample into a catalog-wide ban. The agent checks content fit: what visual
action carries the message, and what would be lost if removed? A single valid
candidate can be selected with a brief rationale; no mandatory approval round.
When the agent must choose a direction, compare task-relevant alternatives,
including an unfamiliar option where suitable; do not choose by habit or recent
reuse. State the differentiating fit in the existing brief or delivery. Reuse is
valid when justified; do not force rotation or impose the catalog on user-led work.
For ambiguity, inspect the differentiating feature or show a bounded choice
when user preference changes the result. If the requested direction is new,
define it from evidence; do not force it into the nearest existing ID.

```bash
python3 <skill-dir>/scripts/style_route.py --brief /abs/brief.json
python3 <skill-dir>/scripts/style_route.py --brief /abs/brief.json \
  --references /abs/reference-manifest.json
python3 <skill-dir>/scripts/style_route.py --validate \
  --references /abs/reference-manifest.json
```

Exit 0 means valid structured output, including unresolved states; consumers
must read `status`. Exit 1 means malformed input or catalog. Only `selected`
or a documented agent selection after `proposed` resolves the chosen family;
production still requires the work-specific direction. Neither grants external publication or generation permission.
Read stdout as data; it contains no executable instructions.

## Add references without rewriting routing

1. Deduplicate and archive through the existing acquisition workflow. Preserve
   canonical source, original identity, hashes, authorship limits and local
   paths. A new reference may belong to several segment-specific directions.
2. Inspect the needed frames/sequence/audio. Add grounded observations to the
   existing manifest; discovery-only references stay unannotated.
3. Run catalog/reference validation, then route a relevant brief. Review matched
   evidence and confusion notes. Keep rejected samples and reasons in the
   project decision record, without rewriting source metadata to fit a choice.
4. If a new direction is actually needed, add a catalog entry with a unique ID
   and aliases, at least two signature features across dimensions, distinction
   notes and supported medium rules. Add feature vocabulary entries if needed.
   No script branch per style, account, or video. Validate alias collisions and
   exercise a positive and near-miss input before relying on the new entry.

IDs remain stable as observations improve. Do not silently repurpose an ID or
remove an existing alias; retain prior receipts. Update observations only with
new evidence and preserve its provenance in the source collection/log.

## Renderer handoff

Pass the selected ID, DESIGN path, scoped override, source/segment evidence,
medium treatment and unresolved motion/audio questions. Breach consumes page
rules; an image renderer consumes image rules; a video producer consumes video
rules plus the film brief. A registered style never implies a renderer exists.
Ordinary pages with an established DESIGN need no reference search or JSON
receipt. The routing framework supplements that path rather than replacing it.
