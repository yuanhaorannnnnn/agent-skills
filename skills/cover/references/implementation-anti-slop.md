# Implementation checks

Read when implementing or reviewing HTML/UI from a project or artifact design.
The filename is retained for existing callers. This file checks whether the
chosen expression works; it supplies no palette, font, symmetry, texture, card,
spacing, transition, or component-style defaults.

## Fidelity to the work

Compare the actual render with the artifact's selected composition, typography,
shape, material and interaction decisions. Fix deviations at their cause.
Do not replace them with a generic template to make implementation easier.
Pure black, saturated or muted colors, symmetry, asymmetry, flatness, texture,
hard cuts and stillness are all available when the work calls for them.

## Functional checks

- Check text at its intended size and viewing conditions: no missing glyphs,
  accidental clipping, unreadable contrast or unintended overlaps. Distinguish
  an intentional crop from losing text needed to understand or use the work.
- Verify hierarchy and reading order; keep numerical comparisons interpretable.
  Text length, viewport changes and localization must not hide required content.
- For interactive elements, verify keyboard operation, visible focus, semantic
  labels and understandable state changes. Do not rely on color alone for status.
- Check actual overflow, scrolling and responsive behavior. Choose layout
  mechanisms and widths from the work's needs, not a prescribed grid or max-width.
- Check loading, empty, error and active states where they exist; choose their
  appearance from the artifact design. Respect reduced-motion preferences.
- Verify content and provenance. Clearly label synthetic/demo data; realistic
  looking sample values are not evidence of actual measurements.

Record technical defects separately from artistic fidelity. A technically valid
render can still fail to realize the work's identity; aesthetic strength cannot
excuse broken interactions or misleading data. Passing these checks does not
establish originality or user aesthetic acceptance.
