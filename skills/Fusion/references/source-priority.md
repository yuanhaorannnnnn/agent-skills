# Source Priority — Information Source Hierarchy

## Priority (never invert)

```
Canon > Local Code > Project Runtime Buffers > Old Wiki / External Web
```

- **Canon** (`/media/yhr/2T/Canon`): cross-project long-term source of truth. Check `index.md`, `projects/`, `tasks/`, `patterns/`, `decisions/`, `incidents/`, `artifacts/` first.
- **Local Code**: current repo — what actually exists, not what docs claim.
- **Runtime Buffers** (repo-local): `.agent-state/MEMORY.md`, Canon task pages, `.agent-state/conversations/`, `.planning/conversations/`, `CLAUDE.md`/`AGENTS.md`, `.agent-state/rules/mistakes.md`.
- **Old Wiki** (`/media/yhr/2T/files/wiki`): historical material only. Cannot override newer Canon conclusions.
- **Agent Workspaces** (`/media/yhr/2T/agent-workspaces/<project>/`): check CLAUDE.md, ARCHITECTURE.md etc.
- **External Web**: community best practices only adopted when not conflicting with local constraints.

## Canon Search Commands

Always search Canon regardless of current working directory:

```bash
# Search all relevant sections
rg -i "<keyword1>|<keyword2>" /media/yhr/2T/Canon/{projects,tasks,patterns,decisions,incidents,artifacts,raw/update-cards} 2>/dev/null

# Check index for missed entries
rg -i "<keyword>" /media/yhr/2T/Canon/index.md /media/yhr/2T/Canon/projects /media/yhr/2T/Canon/tasks 2>/dev/null
```

Read priority: projects/tasks/decisions/patterns/incidents > artifacts/update-cards.

## Runtime Buffer Priority

| Priority | File | Purpose |
|----------|------|---------|
| 1 | `.agent-state/MEMORY.md` | Architecture decisions, known issues |
| 2 | `/media/yhr/2T/Canon/tasks/*.md` | Durable task state |
| 3 | `.agent-state/conversations/*.md` | Historical runtime recaps |
| 4 | `.planning/conversations/*/` | Planning docs (scratch buffer) |
| 5 | `CLAUDE.md` / `AGENTS.md` | Project constraints |
| 6 | `.agent-state/rules/mistakes.md` | Known error patterns |

## Old Wiki / Agent Workspaces (supplementary only)

Only read when Canon + current repo info insufficient:
- `/media/yhr/2T/files/wiki`
- `/media/yhr/2T/agent-workspaces/<project>/`

These are historical sources. Long-term conclusions should be back-written to Canon. `.agent-state/`, `.planning/`, `.research/` stay as current execution evidence only.

## Information Conflict Handling

When Canon conclusion conflicts with external best practice → Canon wins (it's the "already thought through" answer). Flag as 🔴 [conflict] but prioritize Canon.

When local code conflicts with external best practice → local code wins as ground truth. External recommendations must adapt to what the code actually does.

When two external sources conflict → mark both, apply citation verification (Phase 4.4), prefer source with direct evidence over generic advice.
