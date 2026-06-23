---
name: SweepHer
description: |
  CARLA 传感器性能调优的 herdr-native 自动化优化循环。仅当运行在 herdr 环境
  （HERDR_ENV=1）且 CarlaUE5 workspace 内时使用，用 herdr 并行 pane 原语
  （pane run/wait/read）替代传统 Sweep 的阻塞 loop.py 执行层。

  THIS IS THE CARLA HERRD-NATIVE OPTIMIZATION SKILL. Use this whenever the user
  wants to optimize CARLA sensor performance from inside herdr — mentions
  "carla perf", "carla 优化", "传感器调优", "sweep her", "sweepher",
  "调优 LiDAR", "调优传感器", "run carla optimization loop", "sweep carla",
  or any CARLA sensor/lidar tuning task.

  If the user is NOT inside herdr, use the Sweep skill instead.
  If the user is NOT working on CARLA, use Calibrate.
  If the user wants generic "auto optimize" / "性能优化" without specifying
  CARLA, this is NOT the right skill — use Calibrate.
---

# SweepHer — CARLA herdr-native autotune loop

compile→package→server→benchmark→decide 闭环。AI 驱动假设生成 + herdr pane 原语执行 + Sweep loop-policy 判定。

## 和其他 skill 的选择

| 条件 | 选哪个 |
|---|---|
| herdr 内 + CARLA 传感器调优 | **SweepHer**（这个） |
| 不在 herdr / CARLA 传感器调优 | Sweep |
| 通用项目性能优化 | Calibrate |

## 硬规则

1. **HERDR_ENV=1 检查** — 不在 herdr 内拒绝执行
2. **workspace 检查** — 必须是 w4 (CarlaUE5)，否则拒绝
3. **读 reference 再行动**：
   - 改代码前 → `~/.agents/repos/agent-skills/skills/Sweep/references/safety-guardrails.md`
   - 跑 benchmark 前 → `~/.agents/repos/agent-skills/skills/Sweep/references/benchmark-contract.md`
   - 判定 keep/discard 前 → `~/.agents/repos/agent-skills/skills/Sweep/references/loop-policy.md`

## 架构

三层，herdr 做执行引擎：

```
AI 决策层（w4:p1）  — 分析代码、生成假设、写 bench、判定结果
herdr 执行层（p2/pC/pD）— 编译、启动 server、跑 benchmark
Sweep 状态层（YAML）— autoresearch-loop-state.yaml，复用 Sweep 格式
```

## Pane 布局（w4 CarlaUE5 workspace）

```
dev tab (w4:t1)              bench tab (w4:t4)
┌──────────┬──────────┐     ┌──────────┬──────────┐
│ p1       │ p2       │     │ pC       │ pD       │
│ AI 决策   │ Build    │     │ Server   │ Client   │
│ claude   │ shell    │     │ shell    │ shell    │
└──────────┴──────────┘     └──────────┴──────────┘
```

### Pane 命令速查

| Pane | 角色 | 命令 | wait 匹配 |
|------|------|------|-----------|
| w4:p1 | AI 决策 | —（自身） | — |
| w4:p2 | Build | `SKIP_TAR=1 PACKAGE_MODE=full bash package_fast.sh` | `[package_fast] success — package build complete (full)` |
| w4:pC | Server | `cd /media/yhr/2T/CarlaUE5/Build/Package/Carla-0.10.0-Linux-Shipping/Linux && sh ./CarlaUnreal.sh -norelativemousemode` | `Engine is initialized. Leaving FEngineLoop::Init()` |
| w4:pD | Client | 动态（p1 编写/选择），cwd: `.../PythonAPI` | 动态（p1 指定） |

## 状态机

```
[INIT] → [ANALYZING] → [PATCHING] → [BUILDING] → [BENCHMARKING] → [DECIDING]
              ↑                                                        |
              |◄──────── revert + next hypothesis (discard/crash) ─────┤
              |◄──────── update baseline + next hypothesis (keep) ─────┤
                                                                        ▼
                                                                 [TERMINATED]
```

状态文件：`.agent-state/autoresearch-loop-state.yaml`（复用 Sweep 格式）

---

## Phase 1：Init

不改代码。建立 baseline 和 hypothesis queue。

### 1.1 Pre-flight

```bash
python3 ~/.claude/skills/Sweep/scripts/preflight_gate.py
```

blocked → 停止修复。pass → 继续。

### 1.2 确认优化目标

向用户确认：
- **优化目标**（target sensor / pipeline）
- **Metric**（FPS、latency、point count、memory...）
- **维度**（分辨率、通道数、PPS、同步模式...）
- **max_rounds**、**max_duration_minutes**

### 1.3 建立 baseline

无 baseline → 先跑一次 baseline experiment（见 benchmark-contract.md）。

### 1.4 生成 hypothesis queue

分析 codebase，生成 hypothesis 列表，写入 state YAML。

---

## Phase 2：Loop（每轮一个 hypothesis）

p1 是唯一指挥者。以下所有 `herdr` 命令从 p1 发出。

### 2.1 读 safety-guardrails

改代码前必须读 guardrails。

### 2.2 Analyze + Patch

分析当前 hypothesis，打补丁，git commit with hypothesis ID。

### 2.3 Build

```bash
# 启动编译
herdr pane run w4:p2 "SKIP_TAR=1 PACKAGE_MODE=full bash package_fast.sh"

# [p1 不空转] — build 期间并行完成：
#   1. 写/修改 bench 脚本（输出到 pD 的 PythonAPI 目录）
#   2. 确定 BENCH_WAIT_MARKER
#   3. 预读下一个 hypothesis
#   4. 检查 guardrails

# 等待编译完成
herdr wait output w4:p2 \
  --match "[package_fast] success — package build complete (full)" \
  --timeout 600000
```

**build 失败（crash）** → `git revert`，标记 crash，下一个 hypothesis。

> **时序约束**：p1 必须在 build 完成前准备好 bench 脚本和 BENCH_WAIT_MARKER。
> build 通常 5min+，bench 准备 ~1-2min，正常不会倒挂。万一 p1 超时 — server 晚启动几十秒，
> 不丢数据不崩状态。

### 2.4 Start Server

```bash
herdr pane run w4:pC \
  "cd /media/yhr/2T/CarlaUE5/Build/Package/Carla-0.10.0-Linux-Shipping/Linux && sh ./CarlaUnreal.sh -norelativemousemode"

herdr wait output w4:pC \
  --match "Engine is initialized. Leaving FEngineLoop::Init()" \
  --timeout 120000
```

**server 启动失败** → `pkill CarlaUnreal`，revert，标记 crash。

### 2.5 Run Benchmark

```bash
herdr pane run w4:pD \
  "cd /media/yhr/2T/CarlaUE5/Build/Package/Carla-0.10.0-Linux-Shipping/PythonAPI && python ${BENCH_SCRIPT}"

herdr wait output w4:pD \
  --match "${BENCH_WAIT_MARKER}" \
  --timeout 300000
```

**benchmark crash / 点计数不匹配** → revert，标记 discard。

### 2.6 Read Results

```bash
herdr pane read w4:pD --source recent --lines 50
```

解析 metric，对照 loop-policy.md 判定 keep / discard / crash。

### 2.7 数据流总览

```
p1:  run p2 → wait p2 → run pC → wait pC → run pD → wait pD → read pD → decide
p2:  [===== 编译 + 打包 ~5min =====]
pC:                          [== server 启动 ~30s ==]
pD:                                               [=== bench ===]
```

---

## Phase 3：Terminate

全部 hypothesis 跑完或触发终止条件（`round >= max_rounds` / `total_duration >= max_duration_minutes` / `no_improvement_streak >= 3`）：

1. 停 server：`herdr pane run w4:pC "pkill CarlaUnreal"`
2. 打印汇总：best metric、commit、round count、keep/discard/crash 计数
3. best 非 baseline → 提醒用户 push/save
4. Canon promotion：创建 update card

---

## 错误处理

| 场景 | 动作 |
|------|------|
| Build failure | 标记 crash，revert，next hypothesis |
| Server 启动失败 | `pkill CarlaUnreal`，revert，标记 crash |
| Benchmark crash | revert，标记 discard |
| Point count mismatch | revert，标记 discard |
| Patch apply failure | 记录，跳过此 hypothesis |
| All hypotheses tested | Terminate with current best |
| State YAML 丢失/损坏 | 从头 Init |

## p1 时间利用

build 是最慢步骤（~5min）。p1 在这段时间内并行完成 bench 准备，不空转：

```
[启动 p2 编译] → [写 bench(1min)] → [定 marker(10s)] → [预分析下一个假设] → [等编译完成] → [秒接 server]
```

## 依赖

- **herdr** — 执行层引擎，必须 `HERDR_ENV=1`、workspace w4
- **Sweep skill** — 引用其 references（safety-guardrails.md、benchmark-contract.md、loop-policy.md）和 state YAML 格式
- **CARLA toolchain** — `package_fast.sh`、`CarlaUnreal.sh`、Python API
