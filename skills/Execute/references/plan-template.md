# Plan Template

原 Staging 三文件框架（shape → task_plan → findings → progress）退化为 Execute `--plan` 模式的结构模板。当 `--plan` 传入时，Execute 按此模板填充 Canon task page 的 § Plan / § Findings / § Progress。

## § Plan — 对应原 task_plan.md

在 Canon task page 中写入或更新 `## Plan` section：

```markdown
## Plan

### Goal
[一句话描述最终目标]

### Architecture / Decisions
| Decision | Rationale |
|----------|-----------|
|          |           |

### Current Phase
Phase 1: Discovery

### Phases

#### Phase 1: Discovery
- [ ] Understand user intent and constraints
- [ ] Read relevant files and prior context
- [ ] Record discoveries in § Findings
- **Status:** in_progress

#### Phase 2: Planning & Structure
- [ ] Confirm or refine the architecture
- [ ] Define verification strategy
- [ ] Document decisions with rationale
- **Status:** pending

#### Phase 3: Implementation
- [ ] Execute the plan step by step
- [ ] Update § Findings for new discoveries
- [ ] Update § Progress after material changes
- **Status:** pending

#### Phase 4: Testing & Verification
- [ ] Run relevant checks
- [ ] Record test results in § Progress
- [ ] Resolve failures or document residual risk
- **Status:** pending

#### Phase 5: Delivery
- [ ] Review all output files
- [ ] Ensure deliverables are complete
- [ ] Update handoff notes in § Progress if needed
- **Status:** pending

### Validation
- [Verification command or criterion]
```

## § Findings — 对应原 findings.md

在 Canon task page 中写入或更新 `## Findings` section：

```markdown
## Findings

### Requirements
- [Captured requirements]

### Code Observations
- [Files, symbols, behavior, constraints]

### Research Findings
- [External documentation summaries or source-backed findings]

### Open Questions
- [Question]

### Resources
- [URL or file path]
```

## § Progress — 对应原 progress.md

在 Canon task page 中写入或更新 `## Progress` section：

```markdown
## Progress

### Session: YYYY-MM-DD
- **Phase:** [N] [Title]
- **Status:** in_progress
- **Actions:** [Specific action performed]
- **Files:** [file.py] (created/modified)

### Test Results
| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
|      |       |          |        |        |

### Handoff Notes
- [What to do next]
```

## 使用方式

Execute 检测 `--plan` 参数时加载此模板：
- 如果是新 task page：按模板写入 § Plan / § Findings / § Progress
- 如果是已有 task page：更新对应 section，不覆盖已有内容

不传 `--plan` 时不加载——Execute 保持轻量。
