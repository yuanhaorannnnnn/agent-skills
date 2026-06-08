---
name: Tabletop
description: |
  Interactive Markdown document review with visual annotation UI and live agent
  feedback loop. Opens a browser page for section-level annotations. When the
  user submits annotations, the agent receives them, responds in-page, and the
  conversation persists alongside the document.

  Trigger on: "review this doc", "review this document", "标注这个文档",
  "帮我审阅这个方案", "review the plan", "交互式审阅", "doc review",
  "批注这个文件", "标注一下".
---

# Doc Review

## Workflow

### Step 1: Start server + open page

```bash
lsof -i :8766 >/dev/null 2>&1 || python3 <agent-platform>/../projects/review/server.py &
open http://localhost:8766/?file=<absolute-path-to-md>
```

### Step 2: Enter review loop

Call the long-poll endpoint and block until the user submits annotations:

```bash
curl -s "http://localhost:8766/api/wait?file=<path>" | python3 -c "
import sys, json
state = json.load(sys.stdin)
if state.get('ready'):
    print(json.dumps(state['annotations'], indent=2))
"
```

When annotations arrive (after up to 120s), read them.

### Step 3: Respond to annotations

For each annotation, address it directly. Then post your reply back to the page:

```bash
curl -s -X POST "http://localhost:8766/api/reply?file=<path>" \
  -H "Content-Type: application/json" \
  -d '{"text":"<your markdown response>"}'
```

### Step 4: Loop back to Step 2

Go back to `/api/wait` — the user may annotate again based on your reply.
Repeat until the user stops (timeout returns `ready: false`).

### Step 5: Save the review conversation

After the loop ends, save the full conversation as a `.review.md` alongside
the original document:

```bash
python3 -c "
import json, pathlib
p = pathlib.Path('<path>')
annos = json.load(open(p.parent / f'{p.stem}.annotations.json'))
reps = json.load(open(p.parent / f'{p.stem}.replies.json'))
with open(p.parent / f'{p.stem}.review.md', 'w') as f:
    f.write(f'# Review: {p.name}\n\n')
    f.write('## Annotations\n\n')
    for a in annos:
        f.write(f'- **[{a[\"sectionTitle\"]}]** {a[\"text\"]}\n')
    f.write('\n## Agent Replies\n\n')
    for r in reps:
        f.write(f'{r[\"text\"]}\n\n---\n')
print(f'Saved to {p.stem}.review.md')
"
```

## File Layout (alongside the reviewed document)

| File | Contents |
|------|---------|
| `<doc>.annotations.json` | User's section annotations |
| `<doc>.replies.json` | Agent's replies |
| `<doc>.review.md` | Combined human-readable review log |

## Canon 输出边界

读取共享契约：`/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md`。

- Review UI state and annotations are review artifacts. Promote accepted decisions, action items, or document risks to Canon; do not copy transient annotation state by default.
- Canon update-card path, when needed: `/media/yhr/2T/Canon/raw/update-cards/<date>-tabletop-<topic>.md`.
