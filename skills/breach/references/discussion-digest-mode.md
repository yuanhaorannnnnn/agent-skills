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
