# Cross-media design contract

Use when defining a visual identity across pages, images, or video, or when a
project explicitly needs motion or sound direction. Cover owns the design
contract. Each renderer owns its artifact and validation. No video renderer is
installed or invoked by this reference.

For pages and video, resolve the direction through [Style routing](style-routing.md)
when it is not already established. Image generation follows the user's prompt;
do not impose a style family or route it through the catalog unless the user
explicitly requests routing. Honor any style named in the prompt directly. A style is independent from the content format: a launch
film, tutorial, or test report needs its own narrative structure even when it
shares an artistic direction.

## Reference collaboration and ownership

This is the shared rule for combining art references, website specifications
and page-layout examples, including a single HTML artifact. They answer different
questions; none is a compulsory style menu or a complete template for the work.

| Reference | Responsibility | Boundary |
|---|---|---|
| Style catalog and inspected artworks/films | Shape, space, material, color relationships and expressive actions | The catalog is open-ended; a family match does not finish the design |
| awesome-design-md or a relevant existing website specification | Adaptable typography, component, navigation and interaction details | Its palette and visual skin do not override the work's direction |
| html-effectiveness | Reading order, comparison structure, information grouping and spatial examples | Borrow structure as useful; reshape it for the content and art direction |

The producing agent owns the resolved artifact direction and the final result.
It reads project constraints, establishes the reader task and content, then
states a subject-specific visual idea. It studies references only for unresolved
decisions, composes the content structure, and derives concrete tokens and medium
behavior together. Revisit the composition when real content or interaction makes
the initial idea ineffective; do not silently switch to the reference's skin.
There is no requirement to visit all three libraries. Images and films use their
own framing and narrative structure, not an HTML layout lookup.

For each reference actually used, note its exact path/URL, the observed choice,
what is adapted and any relevant inspection limit in the existing brief/evidence.
A source may serve more than one role; do not count it twice. Original decisions
are labelled as such, with their content rationale, rather than attributed to a
reference. Cover's 2–4-source synthesis rule applies when creating/updating a
project specification, not to every artifact or to each reference layer.

### Conflict resolution

- Truthful content, data meaning and required functionality survive aesthetic
  changes. Fix a concrete legibility or interaction defect locally while keeping
  the direction; these requirements prescribe no universal palette or layout.
- Explicit user choices govern the requested scope. Read DESIGN.md to distinguish
  fixed brand constraints from defaults, legacy tokens and per-artifact choices.
  Preserve fixed constraints unless the request authorizes changing them. An
  explicit restyle authorizes an artifact-scoped override, not a project rewrite.
- Within those constraints, the resolved artifact direction governs expressive
  choices. Website tokens and layout examples supply adaptable references. A
  default token conflicting with the direction can be overridden in the brief
  and implementation; record the value/role and scope. Unaffected tokens remain.
- When a serious data chart uses `lieflat-charts`, its data encoding, selected
  template and visual rules govern the chart; the surrounding page's artistic
  direction does not override them. Direct user instructions for that chart
  remain authoritative. Keep page and chart coherent where those rules allow.
- When an illustration uses `hairline-create`, its figure style, engine and
  skill rules govern that figure rather than the surrounding page's artistic
  direction. If they do not fit the work, choose a different illustration
  approach. Direct user instructions for the figure remain authoritative.
- Resolve ordinary design tradeoffs directly. Ask only when two explicit user
  requirements cannot both be met and the missing choice changes the result;
  do not add routine style approval or require a new DESIGN.md for a one-off.

### Who writes and who consumes

The task's producing agent selects the applicable workflow; the user need not
name skills. Invoke Cover when the task needs a new or updated reusable project
specification. Cover writes DESIGN.md and its evidence. For a one-off HTML page,
Breach resolves the brief and scoped tokens, reads the shared contract, and
implements without invoking Cover solely to manufacture a file. Video producers
receive the resolved brief and own their medium-specific output. Image generators
follow the user's prompt, including any explicitly requested project direction.
Breach may present a film review page but does not become the film producer.

Handoff includes the content objective, actual project specification if present,
work-specific visual idea/signatures, reference roles, inherited constraints,
scoped overrides, medium rules and unresolved evidence. Keep this in the existing
brief/conversation/provenance; no extra schema or mandatory file. A renderer may
adapt implementation to preserve the idea, but reports a material departure
instead of silently replacing it. Review the result against this resolved brief.

Examples of decisions (not additional templates):

- Precisionist dynamics report: use a comparison layout for predicted/measured
  behavior; adapt chart controls from a website; let geometric space and hard
  edges organize the page. Never reshape measurement curves to fit the geometry.
- One-off image with a supplied artwork: inspect that work and resolve framing
  and material choices; skip website and HTML-layout libraries.
- Existing fixed-brand page: preserve brand constraints and improve composition
  within them. A legacy palette under `selection-mode: per-artifact` is not a
  fixed brand constraint or a reason to reuse the old work's identity.

## Define identity through choices

Start with what this project should feel like and why that expression fits its
subject. Specify observable choices rather than “premium”, “cinematic”, or
“smooth”: a narrow type column, cut-paper silhouettes, abrupt scale changes,
cobalt fields against black, asymmetric crops, or an audible material texture.
These are examples, not defaults or a checklist to combine.

Record what survives a change of medium and what can change. An identity can
use different colors while retaining its shape vocabulary or compositional
logic. Do not force every artifact into warm paper, soft low-contrast colors,
centered headings, floating cards, or any other safe-looking house template.
Equally, do not ban those techniques when they are deliberate and source-led.

Use one dominant direction per artifact. If a project offers several, name
their uses and define a default or selection rule. Existing brand constraints
remain authoritative until a redesign is requested. Expressive changes may
affect the whole page or film, not just a decorative hero. Preserve data meaning,
readability, focus visibility and truthful evidence within that expression.

## Each artifact has its own identity

A style family is a vocabulary, not a finished design. For each new HTML
artifact or film, the producing agent resolves a work-specific direction before
production, even if a project already supplies tokens. Image generation follows
the user's prompt without requiring a catalog family or extra art-direction step.
Reuse the existing brief
or conversation; no extra file, form, approval round or new style ID is required.

State the work's subject and intended effect, its central visual idea, the
concrete signature choices and how they carry the content. Include what is
being inherited and what this work deliberately does differently from the
nearest available project example. If no comparison exists, say so rather than
claiming measured uniqueness. Do not search the whole world to prove originality.

For HTML, express the idea through composition, typography, imagery and behavior
across the work, not just a decorative hero. For video, give the movement,
editing and sound choices a relationship to the script. A family name plus
colors is insufficient for either medium.

The caller passes this resolved direction along with the project constraints to
the HTML renderer or video producer. For images, pass the user's prompt and any
explicitly requested constraints. A tool's convenient
default must not erase it. A continuous series may intentionally share a visual
identity; distinguish its episodes through their content-driven compositions
rather than random novelty. Editing an existing work preserves its established
identity unless the user requests a redesign.

Inspect the resulting artifact for recognizable choices: does its visual action
or composition explain this particular subject? Would replacing the title leave
an interchangeable generic artifact? If so, revise the idea or composition, not
just the accent color. Distinctiveness is judged on the work, not on a filled
checklist, token count, catalog match or structure gate. Do not guarantee globally
unique style or mistake deliberate ugliness/complexity for originality.

## DESIGN.md extension

Preserve unaffected `colors`, `typography`, and component tokens; explicitly
revise those within the requested redesign scope. Add only fields
needed by the actual brief; this is a small authoring convention, not a new
renderer API or a requirement to fill every slot:

```yaml
art-direction:
  id: chosen-direction
  thesis: "A subject-specific visual idea, stated concretely."
  signatures: ["Observable composition choice", "Shape or material choice"]
  avoid: ["The particular generic treatment that would erase this identity"]
  scope: "Where this direction applies; optional approved alternatives."
medium-rules:
  page:
    composition: "How the identity shapes reading and interface hierarchy."
  image:
    composition: "Framing, subject treatment, and material behavior."
  video:
    motion: "What moves, with what character, and why."
    editing: "How cuts and transitions connect ideas; where to pause."
    typography: "On-screen text hierarchy and readable hold behavior."
    sound: "Sonic character and its relationship to image; silence is valid."
    validation: "proposed; requires a rendered sample"
```

Replace example values with project decisions. Do not add unused medium blocks.
Unverified ideas remain proposed; frame inspection does not validate motion,
musical timing, sound design, or an author's production workflow.

Separate project identity from a particular production brief. Duration, aspect
ratio, resolution, frame rate, channel, caption language, audio delivery and
export format belong to the film brief unless the project genuinely standardizes
them. Never invent universal timing/BPM/transition defaults for a painting style.

## Reference evidence

Retain `.design/evidence.json`'s `references_studied`, `adaptations`, and
`wholesale_copy` fields. References may be exact DESIGN paths, artwork URLs, or
specific film URLs. Select 2–4 distinct sources for synthesis, without pretending
multiple frames from one film are independent sources. Optional
`reference_observations` can record source, asset/frame/timecode, inspection
level (`text`, `frames`, `sequence`, `audio`), observed choice, and proposed
adaptation. Describe creator claims separately from direct observation.

Keep the film or artwork's original authorship distinct from a reposting account.
Source URLs remain useful when assets cannot be bundled. Screenshots used to
study a reference are not automatically production assets or licensed footage.

## Video-production handoff

An available video skill or tool receives:

- Content objective, audience, approved facts and requested deliverables.
- Absolute project DESIGN.md path, resolved family, artifact-specific visual
  idea/signature choices, inherited constraints and scoped override.
- Exact reference URLs/assets with observations and inspection limits.
- Production brief: delivery dimensions/timing/audio requirements known so far;
  unresolved requirements remain visible.

The video owner develops script, storyboard, assets, motion, edit, sound and
export. It returns the actual film path and editable source where available,
with performed validation and unresolved gaps. Breach may present the storyboard
or review page; neither a player nor an animated HTML preview proves a film was
rendered. If no video capability exists, report that boundary and deliver only
the design work actually requested and completed.

## Acceptance

Technical checks cover readability and the requested medium's delivery contract.
For video this includes actual playback/export, text holds, clipping, audio and
sync when audio is requested. Style review asks whether the specified choices
survived, fit the content, and form a recognizable whole without the logo.
Neither review substitutes for the other. “No errors” is not aesthetic approval.

When comparing alternatives, use the same content and deliverable constraints;
vary the artistic choices deliberately. Judge real samples, not adjective lists.
Record `not-run` when no sample was produced, and distinguish author self-review
from user acceptance. Do not make extra samples mandatory for ordinary specs.
