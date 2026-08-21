---
name: tadsim-dynamics-bench
description: |
  CarSim-TadSim 动力学验证诊断工作流。用于 M1-M7 工况：用户只提供 CarSim Run 目录，agent 负责检查 CSV/par、登记 manifest、生成 TadSim replay 命令、用 herdr 的 carla-client pane 执行、等待 Report saved、分析 speed/accel/yaw/brake 分阶段误差，并把问题归因到 CarSim reference、replay parser、wrapper/runtime config、converted parameters 或 TadSim 子模型差异。触发词包括 TadSimDynamicsBench、tadsim bench、CarSim-TadSim、M1-M7 动力学验证、carsim 验证 tadsim 动力学。
---

# TadSimDynamicsBench

## Artifact Mode

读取共享契约：
`/home/yhr/.agents/repos/agent-skills/references/clean-delivery-contract.md`。
原始 CarSim run、parser 诊断和多假设分类属于 `audit` evidence；`summary.md`、
`diagnosis.json` 和 Canon promotion 只有在对应 case 的 accepted replay contract
与验证结果齐全时才作为 `delivery` projection。不要把样本内标定或未验证假设写成
正式结论。

CarSim-TadSim diagnostic benchmark workflow for CarlaUE5. This is not a score-chasing replay tuner. Use it to turn M1-M7 into repeatable evidence that localizes mismatch across the validation chain.

## Scope

Use this when the user provides or references a CarSim run directory for M1-M7 and wants TadSim/Carla dynamics validation.

Operator contract:

```text
Human:
  runs CarSim, exports LastRun.csv/par, gives run directory and maneuver intent

Agent:
  validates CarSim data
  updates benchmark_manifest.yaml when needed
  generates TadSim replay command
  runs via herdr carla-client pane when available
  analyzes report and phases
  classifies the mismatch
  fixes replay/wrapper/config bugs when confirmed
```

## Hard Rules

1. Do not optimize by making plots look good. Diagnose the layer responsible for mismatch.
2. M1 v28 is the current best-shot speed-match evidence. Treat M1 open-loop as diagnostic evidence, not best shot.
3. Do not modify TadSim generated dynamics core just to fit one CarSim curve.
4. If CarSim reference is invalid, stop and tell the user which CarSim dataset/control column to fix.
5. If running pane automation, require `HERDR_ENV=1` and use herdr pane primitives. Do not guess pane IDs; read `herdr pane list`.
6. In CarlaUE5, do not trigger build/package unless the user explicitly asks.

## Repo Harness

Canonical repo path:

```text
/media/yhr/2T/CarlaUE5
```

Repo-local tools:

```text
PythonAPI/test/validation/tadsim/benchmark_manifest.yaml
PythonAPI/test/validation/tadsim/run_carsim_tadsim_case.py
PythonAPI/test/validation/tadsim/analyze_carsim_tadsim_report.py
PythonAPI/test/validation/tadsim/carsim_tadsim_bench.py
```

Read [commands.md](references/commands.md) when you need exact commands or the M2 onboarding sequence.

## Workflow

### 1. Intake

Given a CarSim run directory, check:

```text
LastRun.csv exists
LastRun_all.par / LastRun_echo.par exists if available
Time is monotonic
required columns exist
active controls vary and are not all zero
reference outputs match maneuver intent
```

For a new case, update `benchmark_manifest.yaml`. The user should not hand-edit the manifest.

### 2. Preflight

Run dry-run first:

```bash
python3 PythonAPI/test/validation/tadsim/run_carsim_tadsim_case.py --case M2 --reference-dir <Run_dir> --dry-run
```

If dry-run fails, fix the CarSim reference setup before running TadSim.

### 3. Herdr Execution

If inside herdr, use the bundled script:

```bash
python3 <skill-dir>/scripts/run_in_herdr.py \
  --case M2 \
  --reference-dir <Run_dir>
```

Default pane target is label `carla-client`. The script sends the repo runner command, waits for `Summary saved:` and reads recent output.

If not inside herdr, give the command from dry-run and ask the user to run it in the client terminal.

### 4. Analyze

After report generation, run analyzer if the runner did not already do it:

```bash
python3 PythonAPI/test/validation/tadsim/analyze_carsim_tadsim_report.py \
  --case M2 \
  --report <report.json>
```

Output files:

```text
summary.md
metrics/report JSON from confidence script
diagnosis.json
next_command.sh
```

### 5. Classify

Use this taxonomy:

```text
CarSim reference issue:
  missing columns, inactive control, wrong target speed, wrong maneuver setup

Replay/parser issue:
  wrong column mapping, wrong units, wrong brake proxy, wrong initial state

Wrapper/runtime config issue:
  apply_tadsim_config not applied, control mode mismatch, pressure/0..1 semantics bug

Parameter conversion issue:
  wrong txcar JSON, EV vs ICE mismatch, missing converted parameters

TadSim submodel difference:
  same input and parameters loaded, but engine/TCU/brake/tire response differs
```

### 6. Next Action

Return one of:

```text
rerun CarSim with concrete UI/dataset fix
rerun TadSim with generated command
patch repo code and verify
record model-difference finding
register next M-case in manifest
```

## Current Project State

Current best-shot metrics, accepted replay semantics, API migration state, and
next M-case belong to the Canon task, not this stable workflow contract. Read:

```text
/media/yhr/2T/Canon/tasks/carsim-tadsim-diagnostic-benchmark.md
```

Treat a baseline as current only when that task page links the exact report and
states the comparison boundary. Do not present speed-target/torque-feed-forward
evidence as same-driver-input calibration.
