# Implementation Anti-Slop Rules

Load only when implementing or reviewing UI from a generated `DESIGN.md`.

## Typography

- No browser default fonts or Inter/Arial everywhere. Use distinctive fonts.
- Give headlines presence through size and tighter tracking.
- Keep body text near 65ch maximum and increase line-height.
- Use more than Regular 400 and Bold 700; include Medium 500 or SemiBold 600.
- Use `tabular-nums` or monospace for numeric columns.
- Avoid all-caps subheaders everywhere.
- Use `text-wrap: balance` to avoid orphaned words.

## Color

- Use off-black, charcoal, or tinted dark instead of pure `#000000`.
- Keep accent saturation below 80% and choose one primary accent.
- Keep one warm or cool gray family; do not mix both.
- Avoid generic purple/blue AI gradients.
- Tint shadows to the background hue and keep one light source.
- Add subtle texture when flat surfaces feel synthetic.
- Do not insert an isolated dark section into a light page without design intent.

## Layout

- Avoid fully centered symmetric layouts and generic three-equal-card rows.
- Prefer asymmetric grids, zig-zag composition, or masonry when appropriate.
- Use `min-height: 100dvh`, not `height: 100vh`.
- Prefer CSS Grid over complex percentage-based flexbox math.
- Use a 1200-1440px max-width container for wide screens.
- Do not force equal-height cards unless content requires it.
- Vary border radius by hierarchy and use optical alignment where needed.
- Avoid defaulting every dashboard to a left sidebar.
- Align comparable titles, values, and calls to action.

## Interactivity

- Provide hover, pressed, and visible keyboard-focus states.
- Keep interaction transitions around 200-300ms.
- Prefer skeleton loaders to generic spinners.
- Design empty and error states; never use `window.alert()`.
- Distinguish active navigation.
- Animate with `transform` and `opacity`, not layout properties.

## Content

- Avoid "John Doe" and "Jane Smith" placeholders.
- Use organic sample data instead of fake round numbers.
