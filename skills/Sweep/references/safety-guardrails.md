# Safety Guardrails — Destruction Prevention for Automation Loop

## Must Read Before Any Patch/Build/Benchmark

Sweep is automation. These are hard rules — not "suggestions." Violate any one → terminate the round.

## Gate Scripts

Two gate scripts enforce pre-conditions programmatically:

```bash
# Before loop start — repos, branches, baseline, controller
python3 ~/.claude/skills/Sweep/scripts/preflight_gate.py

# Before each round — worktree clean, state file valid, hypotheses remain
python3 ~/.claude/skills/Sweep/scripts/round_gate.py
```

Both return `pass` or `blocked`. **blocked → do not proceed.** Fix the listed failures before continuing.

## Pre-Round Gate

Before each round, verified by `round_gate.py`:
1. `git status --short` must be clean (no uncommitted changes from prior round)
2. `.agent-state/autoresearch-loop-state.yaml` must exist and be valid YAML
3. Pending hypotheses must be > 0
4. Loop not terminated (streak < 3, round < max)

Before loop start, verified by `preflight_gate.py`:
5. Target repo `/media/yhr/2T/CarlaUE5` + controller repo `/media/yhr/2T/autoresearch` exist
6. Both repos on correct branches, both worktrees clean
7. Baseline metrics.json exists
8. `loop.py` controller exists

## Patch Rules

- Only modify files listed in the current hypothesis's `target_file`
- Never modify `loop.py`, `controller.py`, `external_runner.sh`, or any `carla_autoresearch` infrastructure
- No destructive operations (force push, `git reset --hard` on wrong branch, `rm -rf`)
- Patch scope: single file, single logical change, ≤50 lines preferred

## Build Rules

- Build runs headless via `python3 -m carla_autoresearch.loop build`, ~10 min timeout
- Build failure → mark crash, revert, next hypothesis. Do NOT attempt manual fix.
- Never modify build scripts or Makefiles to force a failing build to pass

## Benchmark Rules

- Benchmark launches via `external_runner.sh` in gnome-terminal — never inline
- Point count mismatch → automatic discard regardless of latency improvement
- Benchmark failure → mark crash, revert, next hypothesis

## Rollback Rules

- **Discard/crash**: `git reset --hard HEAD~1` — revert ONLY the current hypothesis commit
- **Keep**: baseline updated, no revert. Commit stays.
- Never reset past commits that don't belong to the current hypothesis
- If unsure which commit to revert: stop the loop, report to user

## User Interruption

- If user sends message mid-loop: acknowledge, report current state (round/hypothesis/status), wait for instruction
- If conversation compaction occurs: read `.agent-state/autoresearch-loop-state.yaml` on wake to recover state
- If loop state file missing or corrupted: stop, report, do NOT re-initialize without user confirmation

## Termination Safety

- On termination: print final summary (best latency, commit, round, counts)
- If best result is on non-baseline commit: remind user to push/save
- Do NOT auto-push or auto-merge — leave that to the user
