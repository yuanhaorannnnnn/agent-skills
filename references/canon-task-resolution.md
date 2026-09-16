# Canon Task Resolution

Shared resolution logic for reading and writing Canon task pages. All skills that need to find or create a task page MUST use this priority order — do not duplicate or diverge.

## Slug Rules

- demand/bug ID: use the raw ID string (e.g. `JHBN-7679`, `154395`)
- project + branch: sanitize branch name — strip non-alphanumeric chars, replace `/` with `-`, lowercase
- new task: use a concise English semantic slug, kebab-case, max 4 words. For a Chinese-only title, translate its core intent into 2-4 stable English keywords; never create an empty or punctuation-only slug.

## Resolution Priority

### 1. demand_id / bug_id

If the current context tracks a Yunxio demand or bug, the task page is:

```text
/media/yhr/2T/Canon/tasks/<id>.md
```

Examples: `JHBN-7679.md`, `154395.md`.

### 2. Explicit path

User or caller provides a full path or slug. If the path is a slug (no directory), resolve to:

```text
/media/yhr/2T/Canon/tasks/<slug>.md
```

### 3. Project + branch

Use the repo's Canon project slug + current git branch:

```bash
repo_root=$(git rev-parse --show-toplevel)
project=$(basename "$repo_root")
branch=$(git branch --show-current)
candidate="/media/yhr/2T/Canon/tasks/${project}-${branch}.md"
```

Also scan task pages whose frontmatter `project` matches and whose `# Current State` or `## Tasks` content mentions the branch.

### 4. Semantic match

Scan `/media/yhr/2T/Canon/tasks/*.md` and score candidates by:

- frontmatter `title` contains words from the current work description
- frontmatter `project` matches the current Canon project slug
- frontmatter `source` matches the current trigger (yunxiao, user, branch)
- `## Goal` or `## Current State` contains relevant keywords

Pick the highest-scoring match above a minimum threshold. If no candidate clears the threshold, fall through to create new.

### 5. Create new

Generate a kebab-slug from the task title. If the title contains no usable ASCII keywords, first derive a concise English semantic title (for example, `委托模型执行任务` → `delegate-model-task`) and then normalize it:

```python
import re
slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
slug = '-'.join(slug.split('-')[:4])  # max 4 words
path = f"/media/yhr/2T/Canon/tasks/{slug}.md"
```

Create with fresh frontmatter and the required stable-summary sections.

## Merge Contract

When updating an existing task page:

### Stable summary (rewrite every save)

Replace the content of these sections entirely — do not append:

```markdown
## Goal
## Current State
## Next Step
## Key Decisions
```

### Action layer (append/update)

Merge new content into existing:

| Section | Merge Rule |
|---------|-----------|
| `## Tasks` | Toggle `[x]` for completed items; add new items; never delete |
| `## Plan` | Update phase statuses; merge new decisions into table |
| `## Findings` | Append new findings; deduplicate |
| `## Progress` | Append new entries at top (newest first) |
| `## Artifacts` | Add new entries; mark stale with `~~strikethrough~~` |
| `## Evidence` | Add links; never remove | **Optional** |
| `## Timeline` | Append dated entries (newest first) | **Optional** |

### YAML frontmatter

Update on every save:

- `updated`: current date
- `status`: reflect current phase
- `artifacts`: append new paths, deduplicate

## Common Implementations

### Workflow skills — write task pages

`sanitize`, all `execute` modes, `tasking`, and `repair` resolve the task page and apply the action-layer merge rules for their sections. Every Execute mode also records its routing mode, resolved route, reason, models, scope, status/evidence, and delegation depth in `## Routing`; `execute --goal` adds a runtime brief; `execute --plan` additionally owns the Plan/Findings/Progress structure. Ad-hoc work updates the resolved Canon task page directly using the same contract.

### passdown — attaches hot context

Resume from the resolved Canon task page, surface the stable summary and first incomplete task, then invoke passdown when hot runtime context is needed.

## Runtime-Neutral passdown

Skills that need hot session context should call passdown in a runtime-neutral way:

```text
Invoke the passdown skill with --focus matching the task title.
The passdown skill auto-detects the source runtime from available session
JSONL files (Claude Code, Codex, Pi) and extracts the most relevant turns.
```

Do not hardcode `--former claude` or a specific runtime path. passdown's extractor discovers available sessions across runtimes.
