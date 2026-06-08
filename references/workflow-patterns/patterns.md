# Workflow Patterns

Each pattern has a small recipe. Combine sparingly.

## classify-and-act

Use when the input must be routed before action.

- Shape: classifier -> route -> specialized action.
- Use when: task type, severity, owner, or mode is uncertain.
- Avoid when: the user already gave a precise mode.
- Stop: every item has a class and next action.
- Output: `{item, class, confidence, action, evidence}`.

## fan-out-and-synthesize

Use when many independent units benefit from clean contexts.

- Shape: split units -> parallel workers -> synthesis barrier.
- Use when: claims, files, sessions, tickets, candidates, modules.
- Avoid when: units share mutable state or one global invariant dominates.
- Stop: all workers returned structured outputs or timed out.
- Output: `{unit, finding, evidence, risk, recommendation}` plus synthesis.

## adversarial-verification

Use when the producer should not verify itself.

- Shape: producer -> verifier -> objection resolution -> final.
- Use when: root cause, security, factual claims, design coverage, visual compliance.
- Avoid when: no rubric exists.
- Stop: no P0/P1 objections remain, or objections are explicitly accepted.
- Output: `{claim, verdict, evidence, objection, resolution}`.

## generate-and-filter

Use when quality comes from breadth plus pruning.

- Shape: generate candidates -> dedupe -> score/filter -> shortlist.
- Use when: naming, design directions, hypotheses, solution options.
- Avoid when: there is one obvious constrained answer.
- Stop: shortlist meets rubric and duplicates are removed.
- Output: `{candidate, score, reason, risk}`.

## tournament

Use when several agents can attempt the same task and a judge can compare outputs.

- Shape: N contestants -> pairwise judge -> winner/shortlist.
- Use when: naming, design taste, alternative implementations, strategy critique.
- Avoid when: judging criteria are vague or costly to verify.
- Stop: winner selected or top 3 stable after comparison.
- Output: `{winner, alternatives, judging_rationale}`.

## loop-until-done

Use when work amount is unknown.

- Shape: run pass -> check stop condition -> repeat.
- Use when: flaky tests, triage queues, recurring errors, log cleanup.
- Avoid when: no measurable stop condition exists.
- Stop: no new findings, all tests pass, queue empty, or budget exhausted.
- Output: `{iteration, delta, remaining, stop_reason}`.

## quarantine

Use when untrusted content must be separated from privileged actions.

- Shape: low-privilege readers -> sanitized facts -> privileged actor.
- Use when: public issues, support tickets, resumes, web/Slack content.
- Avoid when: all inputs are trusted local code.
- Stop: sanitized facts are ready and unsafe instructions are ignored.
- Output: `{source, sanitized_fact, risk, allowed_action}`.

## model-routing

Use when intelligence/cost should vary by task complexity.

- Shape: scout/classifier -> estimate complexity -> route model/tool.
- Use when: many subagents, unknown codebase depth, mixed easy/hard units.
- Avoid when: fixed model or token budget is already mandated.
- Stop: route chosen with reason.
- Output: `{unit, complexity, model_or_mode, reason}`.
