# Cross-media design contract

Use for visual design across media, including product pages, software UI, other
pages, illustrations, presentations, documents, charts, maps and video, as well
as project identity and explicit motion or sound direction.
Cover owns the shared design contract. Each producer owns its artifact and
validation. No video renderer is installed or invoked by this reference.

Apply shared judgment to the decisions actually within scope, alongside the
producer's own rules. Explicit user instructions, established identity and
selected specialized module contracts remain authoritative. Faithful edits or
specified imagery do not require a new creative direction or outside references.
For autonomous design, carry the content, visual idea and any observed reference
into the produced artifact. Before delivery, inspect the actual result and its
use context where available; revise concrete defects within scope and disclose
uninspected aspects. A written plan, prompt or automated gate alone cannot prove
the result follows the direction or achieves artistic quality.

## Shared design judgment

When a user rejects the appearance of an autonomous visual design (for example,
“不好看”, “太普通”, or “暖色不好看”), interpret the feedback in the full
task context: naming a color or element does not by itself prescribe a palette
swap or establish a general color preference. Inspect the current work and
consider composition, type, imagery, color and their interaction as relevant.
Explain the observed issue and a proposed direction grounded in actual references;
pause for the user's feedback before making changes that depend on that direction.
Do not present a superficial edit as a redesign. A precise request for a limited
edit or an explicitly chosen direction remains authoritative and keeps its scope.

When the user requests stepwise review, present the content idea, observed
references and concrete choices, actual result and before/after comparison, and
coverage/status at the agreed stages; wait for feedback before dependent work.
The user may combine stages or authorize autonomous progress. This preference
overrides default guidance against approval pauses; it does not impose extra
creative exploration on faithful or explicitly scoped edits.

For any visual creation or edit, including faithful local edits, use the existing
delivery to give a concise read-only evidence hint when a material gap or
version association needs clarification: what actual
output or representative state was inspected; whether that observation can be
associated with the delivered version; and which material views, states, resources
or works were not covered. If the association or coverage is unverified, say so.
Keep these as separate facts: a screenshot, local hash, search result or tool
record alone does not prove the final delivery, complete coverage or quality.
Where the delivery channel supports readback, compare the original bytes or
same-algorithm digest of the object referenced by the actual delivery message
or manifest with the inspected version. An old reference, draft, thumbnail or
the same local path alone does not establish the current delivered object.
For a mutable URL, this comparison covers only the time of readback; a match for
one HTML file does not establish coverage of its scripts, data or other resources.
When that readback is unavailable, keep the association unknown; do not upload
or change delivery channels solely to manufacture a stronger status.
Do not infer that an unrecorded check did not happen, or turn an unknown into a
pass, exemption or automatic block. Follow the producer's medium-specific checks;
this hint adds no new approval, file, reference search or creative exploration.

At the end of a visual creation or edit, record one local self-reported telemetry
event with `python3 /home/yhr/.agents/repos/agent-skills/scripts/visual_telemetry.py record`,
using its closed-value options for medium, content idea, reference,
inspection, delivery readback and coverage. Leave a field `unknown` when the
fact is not known; `not_applicable` is for an actually inapplicable decision,
not for an unobserved one. Use `reported_done` / `reported_match` only for the
work actually performed, not for a prompt or a claimed plan.
For `reference`, `reported_done` requires a reference actually inspected and a
concrete choice informed by it; for `inspection`, it requires the actual result
or relevant state to have been inspected. Use `mixed` for multiple media.
For multiple works, summarize the authorized task conservatively: partial or
unverified work must not be reported as fully completed. Duplicate records are
possible; the recorder does not deduplicate tasks.
The recorder stores no task content, file path, URL or image. Its failure is a warning and does not
change the task outcome. It is not a hook or independent evidence: agents may
omit it, and a report is not proof of attention, complete coverage or quality.
To inspect only the recorded aggregate, use the same script with `report`;
missing records are neither failures nor a count of all visual tasks.

For each work involving autonomous design or redesign, carry the following
through production and the existing delivery, at a depth appropriate to the
work. Do not substitute a checklist or written explanation for the artifact:

1. **Content to idea:** before making it, identify the specific content,
   audience and purpose, then decide what visual relationship, composition or
   behavior will express them. Apply the idea in the actual medium; decorative
   polish alone does not establish a relationship to the subject.
2. **Reference to choice:** inspect real references for unresolved decisions;
   identify what was observed and how it informs a concrete choice for this
   work. Follow explicitly supplied references or an established direction;
   do not claim a reference was inspected if it was not.
3. **Result and comparison:** inspect the actual output in its use context
   when available. For a redesign, compare with the existing work in the
   relevant views and behaviors: state the substantive change and whether
   valued features were retained. Fix regressions within scope or disclose the
   tradeoff. A palette, texture or minor layout adjustment alone is a refinement,
   not evidence of a substantive redesign; report it accurately.
4. **Workload and status:** for multiple works, inventory the scope first, then
   work in small groups sized so each receives these decisions and checks;
   continue through the authorized scope without introducing approval pauses,
   except when the user has requested staged review or a rejected direction
   requires the feedback pause above.
   Treat one or two at a time as a useful starting point, not a universal cap.
   Clearly mark unmade work, incomplete redesigns and uninspected results as
   such; do not count a draft, template rerender or minor edit as a completed
   redesign. Report unavailable checks and unresolved quality concerns.

Use the artifact and existing delivery for evidence, without requiring a new
document, fixed number of variants, or approval beyond the feedback and
user-requested review described above. Faithful execution of an
explicit visual direction, data contract or limited edit keeps its original
scope and does not require a new idea or reference search.

Treat these as complementary decisions, not a fixed sequence or a menu of
artifact-specific exceptions:

- **Work and use:** identify the audience, real content, tasks, medium and
  applicable project identity; distinguish fixed brand choices from defaults.
- **Expression and references:** proactively find and inspect references suited
  to unresolved design decisions, including across disciplines when useful;
  retain established directions for maintenance and honor user instructions.
  Develop a distinctive, artistic and forward-looking direction appropriate to
  the work. Translate observed relationships into concrete decisions and test
  them with real content and key interactions; don't equate a style label,
  reference, decoration or palette change with an achieved direction.
- **Component contracts:** identify any selected module's actual scope and
  contracts, including data, behavior, engine or visual identity. Decide
  whether it fits; integrate around its constraints without extending those
  constraints to the whole work. The specific rules below remain authoritative.

These decisions can revise each other. Preserve user choices and existing
identity as specified below; image generation remains prompt-led. For software
UI, check representative real operating states and recurring tasks as well as
visual expression. A product page and an application can share this judgment
without sharing a layout or visual skin. Use the existing delivery for reference
evidence and tradeoffs; do not add a mandatory document or approval step beyond
the feedback and user-requested review described above.

For pages and video, resolve the direction through [Style routing](style-routing.md)
when it is not already established and the applicable workflow calls for it.
Image generation follows the user's prompt;
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
states a subject-specific visual idea. It studies the selected visual reference
and any other references needed for unresolved decisions, composes the content structure, and derives concrete tokens and medium
behavior together. Revisit the composition when real content or interaction makes
the initial idea ineffective; do not silently switch to the reference's skin.
There is no requirement to visit all three libraries. Images and films use their
own framing and narrative structure, not an HTML layout lookup.

For a recurring series, retain its user-selected visual reference and direction
until the user changes it. For a new independent everyday work, select and inspect
a specific real visual reference suited to the content and medium, unless the
user specifies otherwise; do not make the user pick layout and style in separate
rounds. Study the reference as a whole and identify the work, the relationships
adapted, and material departures in the existing delivery. Do not claim that a
generated concept proves the final artifact has achieved the same quality.

Layout, artwork and design-case references are revisable hypotheses, not a fixed
layout → style → example pipeline. An artwork can change information relationships
as well as appearance; real content and key operations can in turn change which
reference choices are useful. In the existing brief, connect the relationship
actually observed in a reference to a concrete design decision, its visible effect
in the sample, and the relevant tradeoff. Do not freeze the first layout before
testing whether it supports the direction.

For each reference actually used, note its exact path/URL, the observed choice,
what is adapted and any relevant inspection limit in the existing brief/evidence.
A source may serve more than one role; do not count it twice. Original decisions
are labelled as such, with their content rationale, rather than attributed to a
reference. Cover may use one primary source for a project specification; additional
sources must answer specific unresolved questions.

### Conflict resolution

- Truthful content, data meaning and required functionality survive aesthetic
  changes. Fix a concrete legibility or interaction defect locally while keeping
  the direction; these requirements prescribe no universal palette or layout.
- Explicit user choices govern the requested scope. Determine the work’s ownership
  before applying a DESIGN.md; storage under a shared directory alone is insufficient.
  Maintain an existing work’s established direction unless restyling is requested;
  new independent works resolve their own direction. Read an applicable DESIGN.md to
  distinguish fixed brand constraints from defaults, legacy tokens and per-artifact choices.
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

### Content-led imagery

When a work calls for an original illustration or visual asset, identify a
specific relationship, tension, transformation or process in the actual
content that is worth expressing. Form a visual proposition: what relates or
changes in the image, what the viewer notices first, and how composition,
material or action carries that meaning. Distinguish alternative content angles
when useful; select a treatment for this subject and audience, rather than
listing keywords or decorating a generic scene. A suggestive image need not be
a literal diagram or enable readers to guess the subject without a caption.

Choose references to answer a specific unresolved visual or practical question,
not to dictate the entire image. Inspect the actual material, distinguish image
observation from text description, and connect an observed relationship to a
concrete choice and its tradeoff. An art movement is optional vocabulary, not
the starting point or a substitute for an idea. Preserve an explicitly supplied
image prompt or direction and the identity of an existing work; do not impose a
style route on image generation.

The user cites Anthropic's published work as a quality aspiration: its observed
range of subject-specific visual ideas is a calibration reference, not a brand,
palette, template, mandatory source or default style to copy. Other references
may better fit a particular subject. Inspect the generated image on three axes:
its relationship to the subject (including the useful test of whether it could
fit an unrelated subject unchanged); its artistic composition as a whole; and
its suitability in the actual layout, size and crop when available. An image
can be expressive without literally explaining the subject. If it is beautiful
but interchangeable, revise the proposition; if it is accurate but a lifeless
diagram, reconsider the visual treatment. An uninspected context, a prompt or a
passed gate does not establish success. Preserve truthful evidence and report
unverified limits. Scale exploration to the work; do not require multiple
generated variants, a new file or approval for routine work.

When learning from a concrete work, inspect how its elements relate: the dominant
axis, overlap and depth of color fields, scale, type placement, density and empty
space. Translate the relationships as an integrated composition, and let actual
content participate where appropriate; a disconnected motif or palette swap is
not evidence of fidelity. Color temperature and texture are choices, not proxies
for quality. Compare the rendered result with the reference and disclose meaningful
departures and any unverified rendering or medium constraints. Do not require
every artifact to use the same shapes, palette, texture or level of visual drama.

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

For an expressive product direction, also consider what remains when its decorative
layer is removed. If viewing, reading and operation relationships are unchanged,
explain the layer's intended role or revise the translation before claiming that
the direction shapes the product. Decoration can legitimately convey atmosphere
or identity; this is a diagnostic question, not a requirement that every artistic
choice change functionality. A rejected sample does not reject its entire style
family.

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
specific film URLs. Record at least one genuinely inspected primary source; add
other sources when useful without pretending multiple frames from one film are
independent sources. Optional
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
Choose requested samples that challenge the direction with available product
content and key operations, rather than only the easiest hero or ideal data.
Use truthful missing-image, long-content or other relevant states; do not invent
assets or data to make the direction work. A static concept establishes only the
composition and states it shows, not unimplemented interactions or user acceptance.
Record `not-run` when no sample was produced, and distinguish author self-review
from user acceptance. Do not make extra samples mandatory for ordinary specs.
