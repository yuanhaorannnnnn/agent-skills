# Breach discussion digest mode

## Discussion Digest Mode

Use this mode for multi-party threads where the useful output is who argued what, how positions changed, what was decided, and what remains open.

1. Acquire the source with the connected GitHub/Gmail capability, a user-provided transcript, or the available web fetcher.
2. Read `discussion-digest-schema.md` before analysis.
3. Produce schema-compliant JSON. Keep the timeline at 30 entries or fewer, mark at most 8 key events, include at least one decision record, and keep `unresolved` non-empty.
4. Write the auditable intermediate artifact to `raw/discussions/<slug>.json` unless the caller specifies another path.
5. Render deterministically:

```bash
python3 <skill-dir>/scripts/render_discussion.py \
  raw/discussions/<slug>.json -o queries/<slug>.html
```

The bundled `assets/discussion-digest.html` is a default, not a fixed artistic
direction. Resolve the work's artistic direction using the General page style
contract; for a redesign, copy the template into the artifact directory, adapt
its composition, typography and colors without changing placeholders or source
semantics, and pass the copy with `--template`. Keep the structured JSON and
renderer, record the actual template and style route in provenance, and validate
the final output on desktop and mobile. Preserve existing artifacts unless a
redesign was requested. Never substitute invented facts for source content.

For a style-led digest, translate the selected direction into the discussion's
actual relationships: for example, distinguish participant positions, trace a
turning point or show how a decision follows the exchange. Let the direction
shape the relevant structure, type and imagery; a palette change, rounded cards
or decorative header alone do not establish the style. Use a concrete inspected
reference when the direction needs one and record what was actually observed;
do not claim a visual inspection from text-only evidence.

Review the rendered page separately for content and visual expression. Check
that participants, chronology, decisions, unresolved items and source links
remain readable and faithful, and that the selected style's recognizable choices
survive beyond the opening. If a distinctive feature is absent, revise the
composition before delivering; if the result remains uncertain, say so instead
of treating a valid router receipt or a responsive layout as aesthetic approval.
