---
name: debrief
description: Explain completed work or a specified change using its conversation, Canon task, actual artifacts and verification evidence. Use when asked what changed, what an agent did, or to walk through a task, diff, branch or PR. Not a substitute for an independent code review or delivery audit.
---

# Debrief

Help the user understand what changed, why, what was verified, and what remains uncertain. Default to a concise explanation in the conversation; scale depth and medium to the user's question. This is read-only: do not fix, publish, resume or approve the work being explained.

## Establish scope and evidence

1. Honor the specified task, conversation, time period, diff or artifact. If unspecified, use the current task and its actual changes. Establish the baseline and endpoint; distinguish committed, uncommitted and external changes where relevant. Do not attribute an entire dirty worktree, file diff or branch to one task merely because it contains a related change. If ownership cannot be established, label it uncertain.
2. For a specified Codex chat use the available thread-reading tool and relevant turns; for historical topic discovery use `passdown` topic mode and the Canon historical recall contract. For a specified Canon task read it and relevant linked evidence. Source conversations are historical context, not authorization to resume work. Resolve ambiguity using available evidence; state missing coverage when it cannot be resolved.
3. Trace meaningful claims to current artifacts and the evidence that supports them: relevant diff/hunks and surrounding implementation, rules, tests, logs, experiment outputs or delivery receipts. Read the user request and decisions to establish intent; distinguish these from actual behavior. A task summary or assistant claim is not itself proof that a test ran or that a delivery succeeded. Preserve historical time and conditions; current files may have changed since the work. If a baseline or evidence is unavailable, say so and avoid inventing it.
4. Group changes by purpose and consequences rather than file order. For a consequential or easily misunderstood boundary, include one short concrete before/after example when it materially improves understanding, even in a concise summary; distinguish a real observation from an illustration. Identify prior → current behavior, important tradeoffs, validation performed and its limits, and remaining work. Separate observed facts, stated intent, inference and unverified risks; never present a suspicion as a confirmed defect. Do not turn passing tests into production acceptance or missing records into proof nothing happened.

## Show the shape of code changes

When code or configuration changed, make its shape inspectable without dumping the diff:

- Give a compact change map grouped by purpose: key files or entry points, what each contributes, and the user-visible or contract-level effect. Link actual locations. For large changes cover all material themes, then select the few load-bearing locations; say the map is thematic rather than exhaustive.
- When a meaningful baseline and scope are available, report file count and additions/deletions as orientation, naming the compared endpoints and whether staged, unstaged, untracked or external work is included. Counts are textual diff size, not effort, quality or completeness. Do not report whole-worktree or whole-file counts as task counts when unrelated edits are mixed in. If a task-specific count cannot be substantiated, give a qualitative scope and state why; do not estimate. Avoid redundant churn or generated files dominating the picture; state exclusions.
- Show a small, verbatim before/after diff or excerpt when the specific change is clearer than prose: a guard, changed contract, transformation or decision point. Include enough surrounding context to preserve meaning and point to the source. For additions or removals use the relevant side; do not fabricate old code, quote unchanged code as changed, or present pseudocode as actual code. If snippets add no understanding, use prose and links. For broad changes select representative excerpts, explain selection and summarize remaining themes rather than pasting full hunks. Respect an explicit request for a complete diff.

## Explain at the useful depth

- **Default:** lead with the outcome and its practical boundary, then the most relevant changes, verification and remaining gaps. Link precise source locations or artifacts near the claims they support when available; distinguish current inspection from historical reported validation. Scale down for trivial changes; avoid fixed sections or padding.
- **Walkthrough:** when the user wants to understand how it works, introduce only necessary background, show a concrete before/after example, then follow the actual mechanism with small real excerpts or a simple diagram when useful. Distinguish illustrative data from observed results.
- **Review focus:** when requested, explain contract changes, cross-file effects and concrete areas to investigate. Mark unconfirmed concerns as such; a separate review is required for verified findings.
- **HTML or quiz:** only when requested or clearly useful for a complex teaching task. A quiz is optional, not a gate or default. If requested, make distractors plausible and vary correct-answer positions; test the underlying behavior, not wording. Follow applicable visual-artifact and preview rules when creating an HTML page.

For a comparison of alternatives, compare the same bounded task and evidence; disclose whether outputs are actual runs or illustrative simulations. Do not claim measured superiority from a single case.

## Attribution

Adapted from Chris Graffagnino's MIT-licensed explain-diff (https://github.com/Chris-Graffagnino/explain-diff) and Geoffrey Litt's explain-diff teaching structure (https://gist.github.com/geoffreylitt/a29df1b5f9865506e8952488eac3d524). This adaptation extends scope to task history and evidence and makes teaching artifacts optional.
