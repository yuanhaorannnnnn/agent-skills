---
name: task-report-slides
description: |
  Create a task-focused HTML presentation deck after work is finished. Use this
  skill when the user explicitly asks to produce a report, recap, presentation,
  slide deck, share-out, or summary document for the just-completed task or
  project work, especially when the source material should come from repository
  documents such as `.planning/`, `.agent-state/`, `docs/`, `Docs/`, notes, or
  implementation records. This skill is explicit-trigger only: use it when the
  user clearly asks for a report-out artifact rather than when they are still
  doing the work.
---

# Task Report Slides

Create a presentation artifact for a completed task using repository evidence, not memory alone.

The output is a single HTML file designed as a horizontal 16:9 slide deck suitable for presentation and screen sharing.

## Trigger Boundary

Use this skill only when the user explicitly asks for a report artifact, for example:

- "针对这次任务输出汇报文档"
- "我们来整理一个分享演示稿"
- "把这次工作的过程和结果整理成汇报 deck"
- "生成一个 HTML 幻灯片汇报"

Do not use this skill while the task is still being defined or implemented unless the user clearly wants a presentation artifact at that moment.

## Goal

Produce a deck that stays tightly focused on the specific task thread the user just completed.

The deck should help an audience quickly understand:

- what the task was
- why it mattered
- what was done
- what decisions were made
- what changed or was delivered
- what remains risky or unfinished

## Source Of Truth

Start from files, not assumptions.

When gathering material, prefer sources in this order:

1. User-explicitly named files or directories
2. Current task planning files under `.planning/conversations/<conversation-id>/`
3. Current task session files under `.agent-state/conversations/`
4. Repo docs directly tied to the task under `docs/`, `Docs/`, or similar directories
5. Supporting implementation notes, changelogs, or task-specific records

Treat repo-level durable memory as background context only. Do not let it dominate the deck unless it directly explains the task.

## Workflow

1. Resolve the current task thread from the conversation and repository context.
2. Identify the smallest set of files that directly describe that task.
3. Extract only evidence-backed points:
   - objective
   - baseline or problem
   - chosen approach
   - major execution steps
   - outcomes
   - open issues
   - next steps
4. Discard unrelated repository history, side quests, and generic project background.
5. Build a slide outline before writing the final HTML.
6. Turn the outline into a polished single-file HTML deck with embedded CSS and minimal JS only if needed.
7. Run the correctness check before presenting the output.

## Task Scoping Rule

The deck is about the task, not the whole repository.

If the repository contains multiple parallel efforts, keep only the thread that is directly connected to the requested report. When in doubt, choose the narrower scope and explain the omission briefly rather than diluting the deck with unrelated material.

If evidence is insufficient, say so explicitly inside the draft process and ask for the missing files or decisions. Do not invent process, rationale, metrics, or outcomes.

## Slide Structure

Adapt to the task, but prefer a compact structure like this:

1. Title
   - task name
   - time context
   - short one-line summary
2. Context
   - problem, opportunity, or motivation
3. Objective and Scope
   - what this task covered
   - what it intentionally did not cover
4. Approach
   - decisions, architecture, method, or workflow
5. Execution
   - the key steps in chronological or logical order
6. Results
   - outputs, delivered artifacts, measurable effects, or confirmed state
7. Risks / Open Issues
   - remaining caveats, unresolved questions, or validation gaps
8. Next Steps
   - follow-up actions with clear direction

Merge or drop sections when the task is smaller. Do not pad the deck with filler slides.

## Writing Rules

- Write with evidence-backed specificity.
- Prefer concise speaker-facing slide copy over dense paragraphs.
- Use short bullets, short callouts, and clear section titles.
- Every slide should answer one clear audience question.
- If a point is important, connect it to a file-backed fact, decision, or outcome.
- Avoid vague praise, generic process language, and empty retrospectives.

## Visual Direction

The artifact is a presentation, not a plain report and not an art poster.

Aim for a visually intentional deck:

- horizontal 16:9 layout
- strong hierarchy
- restrained copy density
- clear spacing rhythm
- consistent accent system
- presentation-safe contrast

When the task benefits from a more expressive look, borrow visual ambition from `canvas-design`, but keep information clarity in first position. The audience must still be able to present from the slides without fighting the design.

Good defaults:

- one strong visual motif across the whole deck
- one or two accent colors plus neutral structure
- large titles, compact supporting text
- cards, timelines, comparison bands, and evidence panels instead of raw text walls
- subtle motion only if it helps presentation flow and remains self-contained in the HTML

Avoid:

- decorative clutter
- low-contrast text
- giant paragraphs
- novelty layouts that hide the narrative
- visuals that imply facts not supported by the source material

## Output Contract

Generate a single HTML file, preferably named `report-slides.html`, unless the user asks for another filename.

The file should:

- render as a 16:9 slide deck
- be horizontally oriented
- be suitable for browser-based presentation
- work as a standalone file with embedded CSS
- avoid unnecessary external dependencies

If minimal JavaScript is needed for slide navigation, keep it small and self-contained.

## Correctness Check

Before handing off the deck, verify these points:

1. Every major slide is directly tied to the current task thread.
2. No slide introduces unrelated repository work, historical context, or parallel efforts unless clearly labeled as supporting context.
3. Claims about decisions, outcomes, and open issues can be traced back to actual repository evidence or user-provided context.
4. The deck covers the full task arc: objective, execution, result, and next step.
5. The visual treatment improves communication instead of obscuring it.

If any check fails, tighten the scope and remove unsupported content before finalizing.

## Optional Closing Note

If useful, include a final slide with a short "discussion prompts" or "Q&A" section, but only when it helps the report-out setting.
