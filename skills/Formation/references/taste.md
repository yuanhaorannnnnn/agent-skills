# Visual Quality Guardrails for skill-architect

## Core Principle

Topology diagrams must be **honest representations of actual relationships**, not decorative art. Every edge must be justified by evidence from skill descriptions.

## Prohibited

1. **Fake relationships** — Do not draw an arrow between two skills unless their descriptions explicitly mention each other or share a concrete file/resource.
2. **Decorative grouping** — Do not create subgraphs/layers just to make the diagram look balanced. Groups must reflect real functional boundaries.
3. **Symmetric mirroring** — Do not draw bidirectional arrows unless both directions are independently justified.
4. **Orphan padding** — Do not add fake nodes or edges to "fill out" a sparse diagram. Sparse is honest.
5. **Generic labels** — Edge labels like "uses" or "relates to" are too vague. Use specific labels: "triggers", "outputs to", "depends on", "includes step".

## Encouraged

1. **Signal-first** — Start with explicit evidence, then allow careful inference for weak cohesion.
2. **Minimal edges** — Prefer fewer, stronger edges over a dense web of weak connections.
3. **Clear layering** — In architecture mold, place infrastructure at bottom, orchestration in middle, user-facing at top (or reverse, but be consistent).
4. **Meaningful colors** — Use color to distinguish edge types, not for decoration:
   - trigger → orange
   - data → blue
   - depends → gray
   - extends → green
   - includes → purple
5. **Honest degradation** — When cohesion is weak or none, embrace the flat output. A good checklist is better than a bad graph.
