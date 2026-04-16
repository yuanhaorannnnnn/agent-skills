---
name: tech-report
description: |
  Generate a Markdown technical report in academic paper structure for a
  completed task. Use this skill whenever the user asks for a 技术报告,
  技术总结, 方案汇报, research report, or post-task documentation — even if
  they don't explicitly name the skill. Accepts an optional `--conversation`
  parameter to identify the task thread, just like `save-conversation` and
  `restore-conversation`. Sources material from
  `.planning/conversations/<conversation>/` and
  `.agent-state/conversations/<conversation>.md` by default. Do not use while
  the task is still actively being implemented unless the user explicitly wants
  a report artifact at that moment.
---

# Task Report Slides

Produce a Markdown technical report for a completed task, structured like a
concise academic paper. Start from repository evidence, not memory.

## When to Use

Trigger when the user asks for a post-task technical report, for example:

- "输出这次任务的技术报告"
- "整理一个技术总结"
- "把这次工作的方案和实现整理成汇报"
- "生成技术方案文档"
- "给我做一个 recap"

Do not trigger while the task is still being defined or actively implemented
unless the user explicitly wants a report right now.

## Input

Accept an optional conversation identifier:

- Explicit: `--conversation <id>`
- Fallback: use the current conversation identity (same rules as
  `save-conversation` / `restore-conversation`)

The conversation id determines where to look for source material:

- `.planning/conversations/<conversation>/`
- `.agent-state/conversations/<conversation>.md`

If the user names additional files or directories, read those as well.

## Core Principle

The report is about **the task**, not the whole repository. Keep it narrow,
evidence-backed, and written for a technical audience. Structure it like a
lightweight academic paper.

## Report Structure

Generate a single Markdown file, preferably `report.md` or
`<conversation>-report.md`. Use the following 6-section structure:

### 1. Abstract
- Task background and motivation
- What problem was being solved
- High-level preview of the chosen approach and key outcome

### 2. Related Works
- Preliminary research and pre-work done before the final decision
- Alternative approaches considered
- Brief comparison matrix or discussion of why alternatives were rejected

### 3. Method
- Final technical selection and rationale
- Detailed design and architectural decisions
- Constraints, trade-offs, and assumptions

### 4. Implementation
- Actual execution process
- Code architecture and module organization
- Key data structures and data flows
- Any important implementation details or tricky integrations

### 5. Evaluation
- How the solution was tested
- Quantitative or qualitative results
- Benchmarks, verification steps, or regression checks
- Comparison against the baseline or acceptance criteria

### 6. Conclusion and Future Work
- Summary of what was achieved
- Remaining risks, known limitations, or open questions
- Clear next steps and future improvement directions

## Workflow

1. **Identify the conversation**
   - Use `--conversation` if provided.
   - Otherwise resolve the current conversation identity (same fallback chain
     as `save-conversation`).

2. **Gather evidence**
   - Read `.planning/conversations/<conversation>/` (especially `spec.md`,
     `task_plan.md`, `findings.md`, `progress.md`).
   - Read `.agent-state/conversations/<conversation>.md`.
   - Include any user-explicitly named files.
   - Treat `.agent-state/MEMORY.md` and other repo-level durable memory as
     background context only.
   - If evidence is insufficient, say so and ask for the missing files or
     decisions. Do not invent process, rationale, metrics, or outcomes.

3. **Map evidence to sections**
   - **Abstract**: pull from the objective and final outcome.
   - **Related Works**: pull from early planning, rejected alternatives, and
     pre-research notes.
   - **Method**: pull from the final spec and architecture decisions.
   - **Implementation**: pull from commit history, code changes, and progress
     notes.
   - **Evaluation**: pull from test results, benchmarks, and verification logs.
   - **Conclusion**: pull from outcomes and any explicitly recorded next steps.

4. **Write the Markdown report**
   - One `.md` file with the 6 sections above.
   - Use clean hierarchical headers (`#`, `##`).
   - Keep prose concise and technical.
   - Include code snippets, diagrams-as-text, or tables where they clarify the
     argument.

5. **Run the correctness check**
   - Verify every section is tied to the current task thread.
   - Verify no section introduces unrelated work unless labeled as supporting
     context.
   - Verify claims trace back to actual repository evidence.
   - Verify the report covers the full arc from research through evaluation to
     next steps.

## Writing Rules

- Use concise, technical prose.
- Connect important points to file-backed facts, decisions, or outcomes.
- Prefer bullet lists and short paragraphs over dense walls of text.
- Avoid vague praise, generic process language, and empty retrospectives.
