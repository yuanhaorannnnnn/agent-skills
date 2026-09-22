# Chart: build a software Study Hub

`chart` is a human-facing workflow for studying a software project, tool,
platform, or product as a versioned, inspectable system. It connects three
evidence layers:

```text
official docs  →  source implementation  →  local runtime evidence
      claims             behavior                 reproduction
```

The result is a Study Hub that explains what the system is, how its important
data and lifecycles work, what the current version supports, and which
questions remain unverified. Documentation is not treated as proof of runtime
behavior.

## The workflow

1. **Pin scope and versions.** Record the learning goal, installed version,
   source commit or branch, and documentation time point. State what is out of
   scope.
2. **Map official sources.** Inventory the official documentation, repository,
   examples, API references, architecture material, release notes, and useful
   tests. Keep third-party material as discovery or explanation, not as the
   normative source.
3. **Model the system.** Describe components, ownership of state, and key
   lifecycles before making a feature checklist.
4. **Triangulate docs → source → runtime.** Attach evidence to each important
   conclusion. Mark runtime work as `pending` when it has not been reproduced.
5. **Track mastery.** Record whether you can use, explain, diagnose, and extend
   each relevant area, with a concrete next piece of evidence.
6. **Split only real follow-ups.** Create a dated topic query when a specific
   unresolved problem appears; do not rewrite the entire documentation site.

## A generic example

Suppose the subject is an HTTP client library and the goal is to maintain it.
The Hub might map the request API and timeout documentation, then locate the
request state machine and retry policy in source. A minimal runtime study would
run one request against a controlled local endpoint, capture timeout and retry
behavior, and record the exact version and command. The Hub would keep these
claims separate:

- **Docs:** the documented timeout and retry contract.
- **Source:** the functions and state transitions implementing that contract.
- **Runtime:** the behavior observed in the controlled test, or `pending` if
  the test was not run.

This example illustrates the evidence shape; it does not claim a particular
library's behavior.

## Expected artifacts

```text
queries/YYYYMMDD-<software>-study-hub.md
raw/collections/YYYYMMDD-<software>-study-sources.json
raw/articles/...                         # archived official pages
queries/YYYYMMDD-<software>-<topic>.md   # only when needed
.research/<chart>/                       # commands, results, screenshots
```

The Hub normally includes learning goals, a one-sentence model, version
boundaries, documentation inventory, docs-to-source mapping, current-environment
limits, a mastery matrix, discussion, and source links. The source record keeps
the official home and repository, installed version, source snapshot,
documentation inventory, archived pages, and evidence state together.

## Boundaries

Use [`acquisition`](../acquisition/SKILL.md) for an article, paper, course,
media item, or collection whose content is the object of study. Use `chart` when
the software itself is the object and docs, source, and runtime are distinct
evidence layers. An acquisition handoff can provide context, but `chart` still
establishes source identity and version boundaries independently.

Use neither workflow for a one-off factual question or a direct code change.
For implementation work, follow the repository's engineering workflow; for a
single answer, answer the question at the required evidence depth without
creating a Study Hub.

## Related files

- [`SKILL.md`](SKILL.md): the agent-facing trigger, workflow, artifact shape,
  and completion gates.
- [`manifest.yaml`](../../manifest.yaml): the repository's skill registry.
- [`README.md`](../../README.md): repository-level orientation.
