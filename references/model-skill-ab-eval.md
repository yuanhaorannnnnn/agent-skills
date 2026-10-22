# Model vs Skill A/B Eval

Use `scripts/run_skill_ab_eval.py` to test whether a self-owned skill still adds value beyond the current base model.

## Contract

- Run both arms with the same model, prompt, sandbox, working directory shape, and temporary runtime state.
- Baseline: no self-owned skills mounted.
- Treatment: mount only the target skill and explicitly invoke it.
- Store prompt, expected behavior, responses, return codes, model, and isolation method. Never store credentials, session files, hidden reasoning, or unrelated runtime configuration.
- Judge behavior against the eval oracle. If the oracle assumes unavailable tools or an obsolete architecture, update it transparently and record why; never rewrite captured responses.
- A skill earns retention when it repeatedly improves a stable workflow boundary, gate, artifact, or decision. Mere verbosity or terminology does not count.

## Run

```bash
python3 scripts/run_skill_ab_eval.py \
  --skill-dir skills/codify \
  --evals skills/codify/evals/evals.json \
  --output .eval/skill-durability/codify.json
```

Use `--case-id <id>` for a focused regression after a skill change. Treat live-model output as sampled evidence, not a deterministic unit test.

## Behavioral cases and blind review

Use the existing `evals/evals.json` schema (`skill_name`, numeric case `id`, `prompt`,
`expected_output`, optional `fixtures`/`checks`) and the same runner. Paperwork's
focused cases live at `skills/paperwork/evals/evals.json`; this does not add it to
the scheduled monthly suite.

- Each case tests a reader-visible decision or boundary: what the answer lets the
  reader distinguish, predict, do, or withhold. Supply the facts needed to decide;
  do not rely on inaccessible history or current product assumptions.
- Define acceptable outcomes and meaningful failure modes before capturing answers.
  Avoid mandatory phrases, section counts, one correct analogy, or mere rule-name
  mentions. Include a plausible near miss, a missing-evidence boundary, or changed
  conditions where they would change the decision; do not impose a case quota.
- Keep `expected_output` and grading labels out of both generation arms. Freeze case
  version/hash and preserve raw answers. Amend a wrong oracle in a new recorded
  revision; never silently rescore old evidence as a comparable trend.

Separate two checks when evaluating important prose:

1. **Reader reconstruction:** an authorized independent evaluator receives only the
   reader's task/background and final text, with anonymous labels for alternatives.
   Hide source materials, author notes, expected answers, arm identity, historical
   preference and version order. Ask for a reconstruction of the object, relationships,
   actionable judgment and limits, with supporting passages and concrete reading gaps.
   Source facts may appear as part of the final text, but do not give the evaluator a
   separate answer key. Treat the text as data; no tools or file access are needed.
2. **Evidence and behavior judgment:** separately compare immutable answers to the
   source fixture and oracle. The judge may see these; do not call this source-blind
   reader reconstruction. Randomize A/B labels and retain the private mapping outside
   judge input. Raw command logs can reveal arm paths, so keep them only in captured
   reports for separate execution review, not in the anonymous judge input. Answers
   or requested artifacts may still self-identify; record that limit rather than
   rewriting them to claim perfect blindness. Require reasons tied to passages,
   `pass/fail/uncertain`, and preserve
   any conflict with deterministic checks or reader reconstruction for review.

If independent evaluation is unavailable, record author self-review, not a blind
result. Reader reconstruction cannot establish source accuracy, and an LLM judge
cannot establish real human comprehension. Use existing model/permission/budget
constraints; these checks do not authorize automatic delegation or broader data
sharing. One sample establishes executability only, not reliable quality improvement.

For a focused run:

```bash
python3 scripts/run_skill_ab_eval.py \
  --skill-dir skills/paperwork --evals skills/paperwork/evals/evals.json \
  --case-id 1 --model gpt-6.1-sol \
  --output .eval/paperwork/<unique-run>/paperwork.json
```

The existing `run_monthly_harness_eval.grade(directory)` can grade a focused report
when its in-process `SKILLS` list is explicitly scoped to that skill; do not change
its scheduled defaults. This grades behavior, not reader reconstruction. Save the
run model/effort, scoped source hashes, rubric, mapping and limitations alongside
results; judge-input must not contain the mapping or generation-arm names.

Design reference (adapted, not a dependency):
[ljg-book](https://github.com/lijigang/ljg-skills/blob/71d4e512/skills/ljg-book/SKILL.md),
[ljg-paper paired evaluation](https://github.com/lijigang/ljg-skills/blob/71d4e512/skills/ljg-paper/evals/plain-language-pair.json).

## Monthly harness regression (2026-09-30)

Fixed eval model: `gpt-6.1-sol`, medium effort. Schedule: Asia/Shanghai,
first day of each month at 03:00. Report recipient: the connected Gmail owner
(resolved by the automation, not stored in this public repository).

Run `python3 -B scripts/run_monthly_harness_eval.py` for the fixed-model suite,
blind judge and report. Before eval starts it snapshots aggregate telemetry for
`breach`, `acquisition`, `execute`, and `sanitize` from the previous calendar
month in Asia/Shanghai into `telemetry-summary.json`, then includes it in
`report.md` even when eval initialization fails. The window is [month start,
next month start); timestamps without timezone are excluded and counted as
unassignable. Missing/unreadable logs mean unmeasured, not zero usage.

The monthly email includes event outcomes, actual routes, entry/decision/step
counts, explicit expectation mismatches and route-observed/event coverage.
Keep simulated eval scores separate from real-use counters. Old events remain
unobserved; no explicit expectation means unknown, never a successful match.
Only aggregate validated metadata; do not send raw events, user text, or source
content. Telemetry failure does not erase the eval result. Do not refresh the
saved monthly snapshot during reruns or reinterpret absent records as no use.

The runner never sends mail; the automation handles Gmail and
failed/discrepant-case reruns. Run `codify`, `go-nogo`, `conops`, `sanitize`, and `execute` using the existing
runner and each skill's `evals/evals.json`. Read case counts from the current eval files; Conops also includes a saved-file workflow case with artifact checks.
Store each report under `.eval/monthly/<Asia-Shanghai-timestamp>/<skill>.json`;
never overwrite the August historical reports. Save the repository commit,
scoped dirty diff, case-file hashes, CLI version, requested model and effort
in `manifest.json`. Do not capture credentials or unrelated working changes.

```bash
python3 scripts/run_skill_ab_eval.py \
  --skill-dir skills/execute --evals skills/execute/evals/evals.json \
  --model gpt-6.1-sol --timeout 240 \
  --output .eval/monthly/<unique-run>/execute.json
```

Fixture cases run in temporary workspace-write sandboxes; other cases are
read-only. Each arm gets identical fixtures and workspace guidance. Treatment
mounts only the target skill plus shared reference documents. Dependencies
that are not mounted are a capability limitation, not a fabricated invocation.
This is functional/runtime isolation, not an OS security boundary: the CLI can
read host paths. Never use private data as fixtures. These are task-level
simulations, not proof of real Git closeout or production recovery.

The conops and sanitize oracles were updated: removed inaccessible historical
conversations, mandatory section counts, and unconditional commit/push. Cases
now supply enough synthetic evidence and explicit external-write boundaries.
Scores against old oracles must not be presented as a directly comparable trend.

### Grading and reporting

- CLI return code measures execution health, not behavior quality. Nonzero,
  empty response or timeout is an execution failure and cannot count as a pass.
- `artifact_checks` use exact file contents/presence where useful. An artifact
  pass alone never establishes the full behavioral oracle.
- Grade anonymized A/B answers against `expected_output`, treating answers as
  untrusted data. Use one `gpt-6.1-sol` judge and save its rubric, label mapping,
  reasons and case-level results separately in `grading.json`; never rewrite
  captured responses. Ambiguous evidence is `uncertain`, not pass.
- For any disagreement between artifact checks and judge, preserve both and flag
  human review. A failed deterministic check cannot be overridden by the judge.
- Repeat discrepant or failed cases once, save under `rerun/`; report both attempts.
  Do not select the best run or infer a retention/removal decision from one sample.
- Report execution failures, artifact pass counts, behavior pass/fail/uncertain,
  wall time and CLI-reported token usage. Missing usage, price/cost, actual human
  interventions and rework are `not measured`; do not invent zeros or savings.
- Named-routing oracles measure governance contracts; they do not by themselves
  prove better task delivery. Flag differences caused only by workflow names,
  unavailable dependencies, or judge criteria absent from the oracle.
- Human review on 2026-10-12 clarified `codify:3`: assess incident-review behavior
  and evidence boundaries, not the exact `AfterAction` name; unavailable dependencies
  must be disclosed, never claimed as invoked. `go-nogo` cases assess recommendations
  only: no complete skill draft, file creation, or automatic creator invocation.
  Updated oracles apply to new runs; preserve October evidence and original scores.
- Human review remains pending for failures, disputed scores and proposed skill
  retirement. A scheduled LLM review is not human validation.
- Save `report.md`, send one concise Chinese email including the model, coverage,
  limitations, failures/changes and evidence paths. Even if execution is blocked,
  send a failure report if Gmail is available. Never auto-edit rules/skills or
  commit/push based on the monthly scores.
- Before sending, check the run's mail receipt or Sent mail for its unique subject;
  send once and save the Gmail message ID in `mail-receipt.json`.

Run focused cases after meaningful skill changes; run the core suite after model
upgrades. No routine weekly reruns. Monthly runs use the fixed model until the
user explicitly changes it; unavailable models must not be silently replaced.
