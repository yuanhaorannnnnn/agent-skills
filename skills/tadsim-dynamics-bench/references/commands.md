# TadSimDynamicsBench Commands

## M2 Onboarding

User gives:

```text
M2 数据在 /media/yhr/2T/files/stuff/M2/Run_xxx
M2 是 <maneuver intent>
```

Agent does:

1. Inspect `LastRun.csv` and par files.
2. Update `PythonAPI/test/validation/tadsim/benchmark_manifest.yaml` with `M2.diagnostic`.
3. Dry-run.
4. Execute through herdr if server is ready.
5. Analyze report.

## Dry Run

```bash
cd /media/yhr/2T/CarlaUE5
python3 PythonAPI/test/validation/tadsim/run_carsim_tadsim_case.py \
  --case M2 \
  --reference-dir /media/yhr/2T/files/stuff/M2/Run_xxx \
  --dry-run
```

## Herdr Run

```bash
python3 <skill-dir>/scripts/run_in_herdr.py \
  --case M2 \
  --reference-dir /media/yhr/2T/files/stuff/M2/Run_xxx
```

Options:

```text
--client-pane carla-client     pane label or pane id
--timeout-ms 600000            wait timeout
--dry-run                      only ask carla-client pane to dry-run the repo runner
--output-dir <dir>             override output directory
```

## Analyze Existing Report

```bash
cd /media/yhr/2T/CarlaUE5
python3 PythonAPI/test/validation/tadsim/analyze_carsim_tadsim_report.py \
  --case M1 \
  --report confidence_results/M1_openloop_driver_table_ice_v1/M1_openloop_driver_table_ice_v1.json
```

## Expected Artifacts

```text
confidence_results/<case>/next_command.sh
confidence_results/<case>/<case>.json
confidence_results/<case>/<case>_speed.png
confidence_results/<case>/<case>_accel.png
confidence_results/<case>/diagnosis.json
confidence_results/<case>/summary.md
```

## Failure Interpretation

- `control columns did not vary`: CarSim dataset not active. Fix CarSim UI before TadSim.
- report uses `txcar_EV`: rerun with converted ICE par path.
- `brake_response_too_strong`: inspect wrapper/runtime config and brake input semantics before tuning gains.
- no `Report saved`: inspect `carla-client` recent output and server status.
