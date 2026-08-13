# Benchmark Contract — Metrics Format & Execution Protocol

## Baseline Metrics

```bash
cd /media/yhr/2T/autoresearch
python3 -m carla_autoresearch.experiment \
  --workspace runs/baseline \
  --description "baseline for autoresearch loop"
```

Baseline metrics.json is required before loop init. No baseline → no loop start.

## Metrics JSON Required Fields

| Field | Description |
|-------|-------------|
| `scan_latency_ms_median` | Primary metric — median LiDAR scan latency in ms |
| `point_count` | Point count consistency check — any mismatch = discard |
| `beam_count` | LiDAR beam count |
| `fps` | Frames per second |
| `timestamp` | Benchmark timestamp |

## Workspace Directory

```
/media/yhr/2T/autoresearch/runs/<loop_id>/
  ├── r1/
  │   ├── metrics.json
  │   ├── build.log
  │   └── benchmark.log
  ├── r2/
  │   └── ...
  └── status.json
```

## Benchmark Execution Protocol

### Launch
```bash
python3 -m carla_autoresearch.loop benchmark-launch \
  --workspace runs/<loop_id>/r<round>
```
Opens gnome-terminal running `external_runner.sh` — handles server startup, benchmark, and server shutdown independently.

### Poll
```bash
python3 -m carla_autoresearch.loop benchmark-poll
```
Check `status.json` for: `starting_server` / `running_benchmark` / `success` / `failed`.

### ScheduleWakeup Pattern
- Initial delay: 120s (server startup + benchmark ~60-90s)
- On wake, poll status
- `success`: proceed to Analyzing Results
- `failed`: mark crash, revert, next hypothesis
- `starting_server` / `running_benchmark`: ScheduleWakeup 60s, idle again

## Decide Contract

```bash
python3 -m carla_autoresearch.loop decide \
  --metrics-path runs/<loop_id>/r<round>/metrics.json
```

Output: `status` (keep | discard), `reason`, `candidate_latency_ms`, `baseline_latency_ms`.

## Current Fixed Contract

- Town05, static ego + static lidar
- Primary metric: `scan_latency_ms_median`
- Point count consistency mandatory

## Artifact Refs

Benchmark outputs referenced by absolute path. Never copy metrics JSON, build logs, or benchmark logs into Canon by default.
