# Clean Delivery Contract

This contract is the shared boundary for self-built skills that produce a
durable artifact. It applies to HTML, Markdown, JSON, code, diagrams, and
handoffs.

## Modes

- `delivery`: the artifact describes the accepted final state. Inputs are an
  `accepted_spec` or an equivalent approved brief plus the implementation,
  diff, and test evidence. Rejected proposals, correction dialogue, and
  discarded alternatives are not output content.
- `audit`: the artifact intentionally preserves history, evidence, hypotheses,
  participants, or rejected alternatives. This is the mode for incident
  reviews, discussion digests, and raw investigation material.
- `knowledge`: the artifact preserves a source chain and separates source
  claims, evidence, interpretation, and reader discussion. It is not a clean
  implementation delivery.

## Delivery rules

Every delivery-producing skill must make these four fields explicit in its
input or gate:

1. `artifact_mode: delivery`;
2. an accepted specification or approved final brief;
3. a bounded scope and acceptance contract;
4. evidence tied to the final artifact (diff, tests, or source citations).

The renderer receives the accepted state, not the full correction transcript.
The final artifact must use final-state names and explanations. Do not encode
negative residue such as “without X”, rejected approach names, prompt history,
or a correction narrative unless the final diff removes a real implementation
or compatibility requires the explanation.

Do not implement this contract with a global forbidden-word scan. A rejected
term may legitimately occur in source citations, compatibility notes, tests,
or audit artifacts. Use the input boundary and the approved-spec gate instead.

## Ownership

- `execute` authors the accepted specification for direct code-development
  runs after the user has confirmed the final scope, constraints, and
  acceptance criteria.
- `conops` authors the approved brief or accepted specification for standalone
  technical-design documents after the design discussion is settled.
- `breach` consumes that final input and owns HTML rendering; it does not infer
  a replacement specification from a correction transcript.
- `passdown` is context transfer only. It may preserve audit history and does
  not create or validate a delivery specification.
- `after-action` is a formal audit artifact. It uses incident and fix evidence,
  not a delivery specification, because material failed attempts and chronology
  are part of its purpose.

## Exceptions

`audit` is intentional for `after-action`, Breach discussion digest, SITREP
Materials, incident/repair evidence, and Passdown history mode. `knowledge` is
intentional for acquisition raw/query notes and paper or source discussions.
These artifacts must still label their mode and must not be mistaken for a
clean delivery.

## Harness spine

```text
accepted_spec / approved brief
        -> skill renderer
        -> artifact + evidence map
        -> Review / Traceback / Sanitize gate
```

For delivery work, the goal brief should include:

```yaml
artifact_mode: delivery
accepted_spec_path: .proposal/<task>/accepted_spec.json
```

Skill-specific instructions may add stronger checks, but may not weaken this
boundary. Runtime files are working state; Canon and the accepted artifact are
the durable source of truth.
