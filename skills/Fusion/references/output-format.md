# Output Format — Report Template & Canon Promotion

## Report Template

```markdown
# Deep Research Report: {topic}

> Scope: {description}
> Sources: Canon ({N} pages), Local code ({N} files), Runtime buffers ({N} sources), Old wiki/external ({N} sources)
> Depth: {light/standard/deep}

## 1. Overview

### 1.1 Core Question
{1-2 sentences — what question does this research answer}

### 1.2 Key Findings (TL;DR)
- Finding 1
- Finding 2
- Finding 3

## 2. Local Current State

### 2.1 Code Structure Overview
{Architecture diagram or directory structure for relevant modules}

### 2.2 Related Implementations

| File | Role | Relevance |
|------|------|-----------|
| ... | ... | ... |

### 2.3 Technical Constraints
{Hard constraints from code and KB}

## 3. External References

### 3.1 Best Practices
{Industry consensus}

### 3.2 Community Solutions
{Open-source reference implementations}

### 3.3 Latest Trends
{2026 new directions}

## 4. Solution Comparison

| Solution | Strengths | Weaknesses | Feasibility | Cost | Recommendation |
|----------|-----------|-----------|-------------|------|----------------|
| A | ... | ... | ... | ... | ... |

## 5. Recommended Approach & Implementation Path

### 5.1 Recommended Solution
{Detailed description}

### 5.2 Implementation Steps
1. Step 1
2. Step 2
3. Step 3

### 5.3 Risks & Mitigations
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| ... | ... | ... | ... |

### 5.4 Key Decision Points
{Decisions requiring user confirmation before implementation}

## 6. Unexplored Areas
{Worth following up but out of scope}

## 7. Sources

### Wiki
- `queries/<slug>.md` — {note}
- `concepts/<slug>.md` — {note}

### Local Code
- `file.py:42` — {note}

### Project KB
- `MEMORY.md` — {note}
- `CLAUDE.md` — {note}

### External
- [Title](URL) — {note}
```

## Save Location

Repo-local `.research/` directory (sibling to `.planning/`):

```
.research/<task-or-topic-slug>/<topic>-YYYYMMDD.md
```

Without clear task, use topic slug:
```
.research/<topic-slug>/<topic>-YYYYMMDD.md
```

## Canon Promotion

Read shared contract: `/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md`.

- `.research/` reports are repo-local artifacts.
- Non-temporary research must create/update `/media/yhr/2T/Canon/raw/update-cards/<date>-fusion-<topic>.md`.
- Merge stable conclusions into relevant Canon project/task/decision/pattern/incident pages.
- One-off questions may output report only — state that Canon promotion was skipped.

## Quality Self-Check

- [ ] Every conclusion has source annotation (use uncertainty markers from Phase 4)
- [ ] Solution comparison includes "local feasibility" dimension
- [ ] Recommended solution has executable steps (not vague "adopt X")
- [ ] Risk analysis covers technical, maintenance, and compatibility risks
- [ ] Language matches AGENTS.md: Chinese prose + English technical identifiers
- [ ] Canon update-card/project/task/decision/pattern refs updated, or explicitly deferred
