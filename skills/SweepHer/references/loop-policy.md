# Loop Policy — Hypothesis Queue, Decisions, Termination

## Hypothesis Queue

All hypotheses generated upfront in Phase 1, tested sequentially. Each hypothesis has:
- `id`: short identifier (e.g., `h1`)
- `description`: what the optimization does
- `target_file`: file path to modify
- `dimension`: optimization dimension (e.g., `model-logic`, `compiler-flags`)

Add to loop state:
```bash
python3 -m carla_autoresearch.loop add-hypotheses \
  --hypotheses "h1:description1:model-logic;h2:description2:model-logic"
```

## Keep / Discard / Crash

decide 命令输出 `keep` | `discard` | `crash`。

**Keep**: 新延迟显著低于 baseline → update baseline, reset streak, record `best`, next hypothesis.

**Discard**: 延迟未改善或 point count 不一致 → revert commit (`git reset --hard HEAD~1`), increment `no_improvement_streak`, next hypothesis.

**Crash**: 构建/benchmark 失败 → revert, increment streak, next hypothesis.

Point count consistency is mandatory — any mismatch = discard regardless of latency improvement.

## Baseline Update

On keep: baseline updated implicitly by loop.py when recording. `best` record tracks: commit hash, latency, round number.

On discard/crash: baseline unchanged. Commit reverted, no state drift.

## no_improvement_streak

Incremented on every discard or crash. Reset to 0 on keep. Termination at ≥3 consecutive failures.

## Termination Rules

Terminate when any:
- `round >= max_rounds` (default: 10)
- `total_duration >= max_duration_minutes` (default: 240)
- `no_improvement_streak >= 3`

Check via:
```bash
python3 -m carla_autoresearch.loop status
```

## Canon Promotion

- Durable results → Canon: benchmark baseline, kept/discarded hypotheses, best commit, crash incidents, artifact paths, follow-up decisions.
- At termination: create `/media/yhr/2T/Canon/raw/update-cards/<date>-sweep-<loop-id>.md`.
- Update relevant Canon task/project/pattern/incident pages.
- Benchmark outputs, metrics JSON, build logs, patches referenced by absolute path.
