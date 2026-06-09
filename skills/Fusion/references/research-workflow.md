# Research Workflow — Phase 0-4 Detailed Process

## Phase 0: Scope Confirmation

### 0.1 Clarify Research Topic

Confirm with user if description is vague:
1. **Topic**: What problem to solve? What technical direction?
2. **Scope**: Which modules/dirs in scope? Which excluded?
3. **Depth**: Quick survey or deep analysis?
4. **Constraints**: Hard constraints (language, framework, version)?

### 0.2 Identify Target Repo

Default to current working directory. If user specifies another repo:
```bash
cd <target_repo>
git status 2>/dev/null && git log --oneline -3
```

### 0.3 Effort Tier

| Tier | Phase 1 | Phase 3 | Time | Guardrails |
|------|---------|---------|------|------------|
| **Light** | 1 grep + 1-2 key files | Optional, 1 quick search | 5-15 min | max 2 thinking rounds, 1 web search, 3 file reads, ≤500 words |
| **Medium** | Standard broad scan + narrow down | Standard (2-3 searches) | 15-30 min | max 4 thinking rounds, 3 web searches, 10 file reads, ≤2000 words |
| **Deep** | Standard + doc-vs-code check | Deep (4-6 searches + cross-verify) | 30-60 min | max 8 thinking rounds, 6 web searches, 20 file reads, ≤5000 words |

**Light** (1 criterion): user asks about a specific function/config/file, answer in 1-2 files, explicitly says "brief".

**Deep** (2+ criteria): involves 3+ files/modules, requires comparing external solutions, needs improvement proposals or comparison matrices, or user mentions "complete analysis"/"architecture"/"extensibility".

**Medium**: default for everything else.

## Phase 1: Local Code Exploration

### 1.1 Broad Scan

1. Agent (explore) or Bash (find/grep) for keywords:
   ```bash
   grep -riE "<keyword1|keyword2>" --include="*.py" --include="*.js" --include="*.ts" --include="*.go" --include="*.rs" . 2>/dev/null | head -50
   find . -type f \( -name "*<topic>*" -o -name "*<related>*" \) 2>/dev/null | head -30
   ```
2. Read top-level architecture docs: `README.md`, `ARCHITECTURE.md`, `CLAUDE.md`
3. Identify 3-5 most relevant modules

### 1.2 Narrow Down

Pick the 1-2 most critical modules for deep reading.

Selection priority: core implementation → similar reference implementations → potential landing-point files.

Actions:
1. Deep-read key files (Read tool, full content)
2. Trace call chain: entry points, callers, dependencies
3. Record findings: code structure, existing implementations, design patterns, constraints
4. **Doc-vs-code check (Deep tier mandatory)**: if design docs exist (`DESIGN.md`, `ARCHITECTURE.md`, `SPEC.md`, `README.md` design sections), compare with actual implementation:
   - Is doc algorithm/flow actually implemented?
   - Is code behavior covered by docs?
   - Mark discrepancies: [doc-code consistent ✅] / [doc says but code missing ⚠️] / [code does but doc silent ❓]

### 1.3 Iterative Deepening (optional)

If new directions emerge, expand back to 1.1. Use sequential-thinking to evaluate ROI of expansion.

## Phase 2: Local Knowledge Base

Three-layer design: Canon → repo runtime buffers → old wiki/agent-workspaces. Read `source-priority.md` for search commands and conflict rules.

### 2.4 Extract Constraints

- Architecture decisions: why is the code designed this way?
- Known issues: pitfalls in this domain?
- Technical constraints: version locks, compatibility, performance floors
- Historical attempts: was something similar tried before?

## Phase 3: External Information

Execution intensity determined by Phase 0.3 effort tier — see the tier table above.

### 3.1 Web Search

1. **Technical docs**: `WebSearch: "<tech> best practices 2026"` / `<tech> official documentation`
2. **Community discussion**: `WebSearch: "<tech> vs <competitor> comparison"`
3. **Reference implementations**: `WebSearch: "<tech> implementation example github"`

### 3.2 Deep Read

Use WebFetch on key pages. Extract: core concepts, best practices checklist, known pitfalls, performance/security/maintainability tradeoffs.

### 3.3 Record External Constraints

Community consensus, anti-patterns, 2026 new directions.

## Phase 4: Synthesis

### 4.1 Sequential-Thinking Detection

If `mcp__sequential-thinking__sequentialthinking` is available → use tool-based mode at these decision points:

**Decision A: Research Direction** — Phase 1 found multiple relevant modules. Evaluate ROI per direction.

**Decision B: Constraint Conflict** — Phase 2 historical constraints conflict with Phase 3 best practices. Analyze priority and feasibility boundaries.

**Decision C: Solution Comparison** — Multiple candidate solutions need local-context evaluation. Hypothesis-verification loop per solution.

**Decision D: Information Conflict** — Local code vs external best practice or conflicting external sources. Resolve conflict, form unified conclusion.

Call format:
```
mcp__sequential-thinking__sequentialthinking:
  thought: "Decision point: XX. Known: A, B, C. Key conflict: X vs Y."
  thoughtNumber: 1
  totalThoughts: 5
  nextThoughtNeeded: true
```

### 4.2 Explicit Thinking Framework (no sequential-thinking MCP)

For Kimi, Pi, Hermes etc. — text-based equivalents at the bottom of this file.

### 4.3 Solution Comparison Matrix

| Solution | Strengths | Weaknesses | Local Feasibility | Cost | Maintenance | Recommendation |
|----------|-----------|-----------|-------------------|------|-------------|----------------|
| A | ... | ... | ... | ... | ... | ... |

Feasibility: **High** (has implementation base, minor changes) / **Medium** (new module/dependency, clear path) / **Low** (conflicts with existing architecture).

### 4.4 Citation Verification

Before output: extract all key assertions → verify source → annotate:
- Local code → ✅ [code confirmed]
- Local KB → 📄 [doc confirmed]
- External web → 🌐 [external]
- No direct source → ⚠️ [inferred] or ❓ [unverified]

High-risk unverified assertions → supplement or mark explicitly. Low-risk → retain with annotation.

Stop condition: all high-risk assertions verified or explicitly marked.

## Explicit Thinking Frameworks (no MCP fallback)

### Iterative Deepening
1. BRIEF OVERVIEW (1-2 sentence current understanding)
2. Identify GAPs (missing info, uncertainties)
3. NARROW DOWN (focus on 1-2 most important gaps)
4. REVISED UNDERSTANDING after exploration
5. Repeat until gaps filled or scope limit reached

### Revision Protocol
Trigger when: new finding contradicts prior conclusion / prior assumption falsified / key constraint was missed / external best practice conflicts with local implementation.

Steps: state original conclusion → state triggering new info → give revised conclusion → note impact on subsequent analysis.

### Hypothesis-Verification Loop
Per candidate: state hypothesis → list verification checklist (code/constraint/compatibility/maintenance) → verify each with Read/Bash → mark result (✅ confirmed / ⚠️ inferred / ❓ unverified).

### Branch Exploration
List branches (max 3) → lightweight explore each (5-10 min) → assess ROI → deep-dive 1-2 high-ROI, record others as alternatives.

### Uncertainty Annotation
- ✅ [code confirmed] — direct code evidence
- 📄 [doc confirmed] — official or project doc evidence
- ⚠️ [inferred] — inferred from code structure, no direct evidence
- ❓ [unverified] — needs further verification
- 🌐 [external] — from web search/docs, not locally verified
- 🔴 [conflict] — contradicts existing info, needs resolution
