---
name: autoresearch-loop
description: |
  Supervised automation loop for CARLA LiDAR performance optimization.
  Use this skill whenever the user wants to run an automated optimization
  benchmark loop, iterate on code optimizations automatically, or set up
  a self-driving performance tuning workflow for CARLA sensors. Also trigger
  when the user mentions "autoresearch loop", "automatic benchmark",
  "optimization loop", "run experiments automatically", or wants AI to
  generate and test optimization hypotheses without manual intervention
  for each build/benchmark cycle.
---

# Autoresearch Loop

This skill orchestrates a supervised automation loop for optimizing CARLA
LiDAR sensor performance. The user provides the optimization configuration;
the AI handles code analysis, hypothesis generation, patch application,
build, benchmark, and keep/discard decisions — iterating until termination
conditions are met.

## Architecture

The loop is split across two layers:

- **This skill (AI layer)**: Analyzes code, generates hypotheses, applies
  patches with Write/Edit tools, makes decisions, and coordinates the loop.
- **`loop.py` (mechanical layer)**: Handles state persistence, build execution,
  external benchmark launching, and result comparison via CLI commands.

State is persisted to `.agent-state/autoresearch-loop-state.yaml` so the
loop survives conversation compaction and can be resumed after interruption.

## Triggering

Trigger this skill when the user:

- Asks to start an optimization loop or automatic benchmark
- Wants AI to generate and test optimization hypotheses
- Mentions `/autoresearch-loop` or similar command
- Wants to iterate on CARLA LiDAR performance without manual build/benchmark
  per round

## Phase 1: Initialize

### 1.1 Verify prerequisites

Before starting, confirm:

1. **Target repository** (`/media/yhr/2T/CarlaUE5`) is on the correct branch
   (`feature/carla-lidar-optimization` by default).
2. **Controller repository** (`/media/yhr/2T/autoresearch`) is on the correct
   branch (`feature/carla-lidar-autoresearch` by default).
3. A baseline metrics file exists (from a prior manual run or the loop itself).
   If not, run one manual baseline experiment first:
   ```bash
   cd /media/yhr/2T/autoresearch
   python3 -m carla_autoresearch.experiment \
     --workspace runs/baseline \
     --description "baseline for autoresearch loop"
   ```

### 1.2 Initialize loop state

Run the init command to create the state file:

```bash
cd /media/yhr/2T/autoresearch
python3 -m carla_autoresearch.loop init \
  --target <target_name> \
  --metric scan_latency_ms_median \
  --dimensions model-logic \
  --max-rounds 10 \
  --max-duration 240 \
  --baseline-latency <latency_from_baseline> \
  --baseline-commit <baseline_commit_hash> \
  --baseline-metrics <path_to_baseline_metrics.json>
```

Parameters:
- `--target`: Name of the LiDAR target (e.g., `RayCastMemsLidar`)
- `--metric`: Primary metric to optimize (default: `scan_latency_ms_median`)
- `--dimensions`: Comma-separated optimization dimensions (default: `model-logic`)
- `--max-rounds`: Maximum optimization rounds (default: 10)
- `--max-duration`: Maximum duration in minutes (default: 240)
- `--baseline-latency`: Baseline median latency in ms
- `--baseline-commit`: Git commit hash of baseline
- `--baseline-metrics`: Path to baseline metrics.json

### 1.3 Generate hypothesis queue

Analyze the target codebase (typically in `CarlaUE5` under the LiDAR sensor
implementation) and generate N optimization hypotheses. Each hypothesis
should include:

- `id`: Short identifier (e.g., `h1`, `h2`)
- `description`: What the optimization does
- `target_file`: File path to modify in CarlaUE5
- `dimension`: Optimization dimension (e.g., `model-logic`, `compiler-flags`)

Add hypotheses to the loop state:

```bash
python3 -m carla_autoresearch.loop add-hypotheses \
  --hypotheses "h1:description1:model-logic;h2:description2:model-logic"
```

## Phase 2: Loop Execution

For each pending hypothesis, execute the following state machine:

```
[INIT] (done in Phase 1)
  |
  ▼
[ANALYZING] ──pop next pending hypothesis──► [PATCHING]
  |                                              |
  |◄───────revert + next hypothesis──────────────┘
  |         (on discard/crash)
  |
  |◄───────update baseline + next hypothesis─────┘
  |         (on keep)
  |
  ▼
[TERMINATED] (max_rounds / max_duration / no_improvement_streak)
```

### 2.1 Patching

1. Read the target file(s) for the current hypothesis.
2. Apply the optimization patch using Write/Edit tools.
3. Verify the change compiles syntactically (if possible, a quick check).
4. Stage changes with `git add`.
5. Commit with a descriptive message including the hypothesis ID.

### 2.2 Building

1. Update loop state to `BUILDING`.
2. Run headless build:
   ```bash
   python3 -m carla_autoresearch.loop build \
     --workspace runs/<loop_id>/r<round>
   ```
3. If build fails (non-zero exit code):
   - Mark hypothesis result as `crash`
   - Revert the commit: `git reset --hard HEAD~1`
   - Proceed to next hypothesis
   - Increment `no_improvement_streak`

### 2.3 Benchmarking

1. Update loop state to `BENCHMARKING`.
2. Launch external benchmark runner (non-blocking):
   ```bash
   python3 -m carla_autoresearch.loop benchmark-launch \
     --workspace runs/<loop_id>/r<round>
   ```
   This opens a gnome-terminal running `external_runner.sh`, which handles
   server startup, benchmark execution, and server shutdown independently.
3. Use `ScheduleWakeup` to poll for completion:
   - Initial delay: 120 seconds (server startup + benchmark typically takes
     60-90 seconds)
   - On wake, poll status:
     ```bash
     python3 -m carla_autoresearch.loop benchmark-poll
     ```
   - If `state == "success"`: proceed to Analyzing Results
   - If `state == "failed"`: mark as `crash`, revert commit, next hypothesis
   - If `state` in `("starting_server", "running_benchmark")`:
     ScheduleWakeup with 60s delay and go idle again

### 2.4 Analyzing Results

1. Read the metrics.json produced by the benchmark.
2. Run the decision command:
   ```bash
   python3 -m carla_autoresearch.loop decide \
     --metrics-path runs/<loop_id>/r<round>/metrics.json
   ```
3. The decision output includes:
   - `status`: `keep` or `discard`
   - `reason`: Explanation
   - `candidate_latency_ms`: New latency
   - `baseline_latency_ms`: Current baseline

### 2.5 Deciding

Based on the decision output:

**If `keep`:**
1. Update baseline to the new result:
   ```bash
   # The baseline is updated implicitly by loop.py when recording
   ```
2. Reset `no_improvement_streak` to 0.
3. Update `best` record.
4. Proceed to next hypothesis.

**If `discard`:**
1. Revert the commit: `git reset --hard HEAD~1`
2. Increment `no_improvement_streak`.
3. Proceed to next hypothesis.

**If `crash`:**
1. Revert the commit: `git reset --hard HEAD~1`
2. Increment `no_improvement_streak`.
3. Proceed to next hypothesis.

### 2.6 Termination Check

After each decision, check termination conditions:

```bash
python3 -m carla_autoresearch.loop status
```

Terminate if any of:
- `round >= max_rounds` (default: 10)
- `total_duration >= max_duration_minutes` (default: 240)
- `no_improvement_streak >= 3` (3 consecutive discards/crashes)

If terminating, summarize results and output the best found optimization.

## Phase 3: Terminate

When the loop terminates:

1. Print final summary:
   - Best latency achieved
   - Commit hash of best result
   - Round number of best result
   - Total rounds executed
   - Total hypotheses tested
   - Keep/discard/crash counts
2. If the best result is on a non-baseline commit, remind the user to push
   or save that commit.
3. Update the conversation recap to reflect the completed work.

## State Persistence

The loop state is stored in `.agent-state/autoresearch-loop-state.yaml`.
Key fields:

| Field | Description |
|-------|-------------|
| `loop_id` | Unique identifier for this loop instance |
| `state` | Current state machine state |
| `config` | Optimization configuration |
| `baseline` | Current baseline metrics and commit |
| `best` | Best result found so far |
| `current` | Current round, hypothesis, workspace paths |
| `hypotheses` | Queue of hypotheses with status |
| `termination` | Streak counters and termination reason |

If the state file is missing or corrupted on load, the loop must be
re-initialized from scratch.

## Error Handling

| Scenario | Handling |
|----------|----------|
| Build failure | Mark `crash`, revert, next hypothesis |
| Server fails to start | External runner reports failure, revert, next |
| Benchmark crashes | External runner reports failure, revert, next |
| Point count mismatch | Decision = `discard`, revert, next |
| Patch apply failure | Log error, skip hypothesis (no revert needed) |
| Git commit failure | Log error, abort round |
| All hypotheses tested | Terminate with current best |

## Key Constraints

- **Build runs headless** in the AI process (subprocess, ~10 min timeout).
- **Server + benchmark run externally** in gnome-terminal, polled via
  `status.json` and `ScheduleWakeup`.
- **Patches use `acceptEdits` mode**: AI applies changes automatically.
- **Hypothesis generation is one-shot**: Generate all upfront, test sequentially.
- **Point count consistency is mandatory**: Any mismatch = discard, regardless
  of latency improvement.
- **Current fixed benchmark contract**: Town05, static ego + static lidar,
  primary metric `scan_latency_ms_median`.

## CLI Quick Reference

```bash
# Initialize
python3 -m carla_autoresearch.loop init --target T --baseline-latency N --baseline-metrics P

# Add hypotheses
python3 -m carla_autoresearch.loop add-hypotheses --hypotheses "h1:desc:dim;h2:desc:dim"

# Run build
python3 -m carla_autoresearch.loop build --workspace W

# Launch benchmark
python3 -m carla_autoresearch.loop benchmark-launch --workspace W

# Poll benchmark
python3 -m carla_autoresearch.loop benchmark-poll

# Decide
python3 -m carla_autoresearch.loop decide --metrics-path P

# Check status
python3 -m carla_autoresearch.loop status
```

## File Locations

- Skill: `~/.agents/skills/autoresearch-loop/SKILL.md`
- Loop controller: `/media/yhr/2T/autoresearch/carla_autoresearch/loop.py`
- Build adapter: `/media/yhr/2T/autoresearch/carla_autoresearch/controller.py`
- External runner: `/media/yhr/2T/autoresearch/carla_autoresearch/external_runner.sh`
- Experiment entry: `/media/yhr/2T/autoresearch/carla_autoresearch/experiment.py`
- State file: `.agent-state/autoresearch-loop-state.yaml`
