---
name: herdr-carla-tune
description: |
  CARLA 传感器性能调优的 herdr-native 自动化优化循环。仅当运行在 herdr 环境
  （HERDR_ENV=1）且 CarlaUE5 workspace 内时使用，用 herdr 并行 pane 原语
  （pane run/wait/read）执行完整调优闭环。

  THIS IS THE HERDR-NATIVE CARLA SENSOR TUNING SKILL. Use this whenever the user
  wants to optimize CARLA sensor performance from inside herdr — mentions
  "carla perf", "carla 优化", "传感器调优", "herdr carla tune", "carla autotune",
  "herdr 传感器调优", "调优 LiDAR", "调优传感器", "run carla optimization loop",
  or any CARLA sensor/lidar tuning task.

  If the user is not inside herdr or is not working on CARLA, do not use this
  skill; continue with the runtime's normal coding and benchmark workflow.
---

# herdr-carla-tune — CARLA herdr-native autotune loop

## Artifact Mode

读取共享契约：
`/home/yhr/.agents/repos/agent-skills/references/clean-delivery-contract.md`。
`.agent-state/autoresearch-loop-state.yaml`、hypothesis queue、keep/discard/crash
记录属于 `audit`；Terminate 阶段提升到 Canon 的 baseline、实际保留改动和验证
结果属于 `delivery`。最终报告不复述被 discard 的实验，除非解释兼容性或安全边界。

compile→package→server→benchmark→decide 闭环。AI 驱动假设生成 + herdr pane 原语执行 + 本 skill 的 loop-policy 判定。

## 和其他 skill 的选择

| 条件 | 选哪个 |
|---|---|
| herdr 内 + CARLA 传感器调优 | **herdr-carla-tune**（这个） |
| 不在 herdr / CARLA 传感器调优 | 使用 runtime 的普通开发与 benchmark 流程 |
| 通用项目性能优化 | 使用普通性能分析与验证流程 |

## 硬规则

1. **HERDR_ENV=1 检查** — 不在 herdr 内拒绝执行
2. **workspace 检查** — live workspace 的 cwd 必须解析为 CarlaUE5；不得依赖
   会压缩变化的 workspace/pane ID
3. **读 reference 再行动**：
   - 改代码前 → `references/safety-guardrails.md`
   - 跑 benchmark 前 → `references/benchmark-contract.md`
   - 判定 keep/discard 前 → `references/loop-policy.md`

## Live Pane Resolution

每轮开始和任何 tab/pane 拓扑变化后重新解析 ID：

```bash
herdr workspace list
herdr tab list --workspace "$WORKSPACE_ID"
herdr pane list --workspace "$WORKSPACE_ID"
```

从 live JSON 中选择 cwd 为 CarlaUE5 的 workspace，再按 pane label/command/cwd
确认并设置 `CONTROL_PANE`、`BUILD_PANE`、`SERVER_PANE`、`CLIENT_PANE`。缺少或
存在多个候选时停止并报告，不猜 ID。ID 只在当前拓扑内有效，不写入长期状态。

## 架构

三层，herdr 做执行引擎：

```
AI 决策层（CONTROL_PANE）— 分析代码、生成假设、写 bench、判定结果
herdr 执行层（BUILD/SERVER/CLIENT_PANE）— 编译、启动 server、跑 benchmark
状态层（YAML）— autoresearch-loop-state.yaml
```

## Pane 角色（CarlaUE5 workspace）

```
dev tab                       bench tab
┌──────────┬──────────┐     ┌──────────┬──────────┐
│ control  │ build    │     │ server   │ client   │
│ AI 决策   │ Build    │     │ Server   │ Client   │
│ claude   │ shell    │     │ shell    │ shell    │
└──────────┴──────────┘     └──────────┴──────────┘
```

### Pane 命令速查

| Pane | 角色 | 命令 | wait 匹配 |
|------|------|------|-----------|
| `$CONTROL_PANE` | AI 决策 | —（自身） | — |
| `$BUILD_PANE` | Build | `SKIP_TAR=1 PACKAGE_MODE=full bash package_fast.sh` | `[package_fast] success — package build complete (full)` |
| `$SERVER_PANE` | Server | `cd <package-linux-dir> && sh ./CarlaUnreal.sh -norelativemousemode` | `Engine is initialized. Leaving FEngineLoop::Init()` |
| `$CLIENT_PANE` | Client | 动态（controller 编写/选择），cwd: `<package-python-api-dir>` | 动态（controller 指定） |

## 状态机

```
[INIT] → [ANALYZING] → [PATCHING] → [BUILDING] → [BENCHMARKING] → [DECIDING]
              ↑                                                        |
              |◄──────── revert + next hypothesis (discard/crash) ─────┤
              |◄──────── update baseline + next hypothesis (keep) ─────┤
                                                                        ▼
                                                                 [TERMINATED]
```

状态文件：`.agent-state/autoresearch-loop-state.yaml`

---

## Phase 1：Init

不改代码。建立 baseline 和 hypothesis queue。

### 1.1 Pre-flight

从 live workspace 和 controller checkout 解析本轮配置；不要把路径或分支写入 skill：

```bash
python3 <skill-dir>/scripts/preflight_gate.py \
  --target-repo "$TARGET_REPO" \
  --controller-repo "$CONTROLLER_REPO" \
  --target-branch "$TARGET_BRANCH" \
  --ctrl-branch "$CONTROLLER_BRANCH"
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

`CONTROL_PANE` 是唯一指挥者。以下所有 `herdr` 命令从该 pane 发出。

### 2.1 读 safety-guardrails

改代码前必须读 guardrails。

### 2.2 Analyze + Patch

分析当前 hypothesis，打补丁，git commit with hypothesis ID。

### 2.3 Build

```bash
# 启动编译
herdr pane run "$BUILD_PANE" "SKIP_TAR=1 PACKAGE_MODE=full bash package_fast.sh"

# [controller 不空转] — build 期间并行完成：
#   1. 写/修改 bench 脚本（输出到 client 的 PythonAPI 目录）
#   2. 确定 BENCH_WAIT_MARKER
#   3. 预读下一个 hypothesis
#   4. 检查 guardrails

# 等待编译完成
herdr wait output "$BUILD_PANE" \
  --match "[package_fast] success — package build complete (full)" \
  --timeout 600000
```

**build 失败（crash）** → `git revert`，标记 crash，下一个 hypothesis。

> **时序约束**：controller 必须在 build 完成前准备好 bench 脚本和 BENCH_WAIT_MARKER。
> build 通常 5min+，bench 准备 ~1-2min，正常不会倒挂。万一 controller 超时 — server 晚启动几十秒，
> 不丢数据不崩状态。

### 2.4 Start Server

```bash
herdr pane run "$SERVER_PANE" \
  "cd $PACKAGE_LINUX_DIR && sh ./CarlaUnreal.sh -norelativemousemode"

herdr wait output "$SERVER_PANE" \
  --match "Engine is initialized. Leaving FEngineLoop::Init()" \
  --timeout 120000
```

**server 启动失败** → `pkill CarlaUnreal`，revert，标记 crash。

### 2.5 Run Benchmark

```bash
herdr pane run "$CLIENT_PANE" \
  "cd $PACKAGE_PYTHON_API_DIR && python ${BENCH_SCRIPT}"

herdr wait output "$CLIENT_PANE" \
  --match "${BENCH_WAIT_MARKER}" \
  --timeout 300000
```

**benchmark crash / 点计数不匹配** → revert，标记 discard。

### 2.6 Read Results

```bash
herdr pane read "$CLIENT_PANE" --source recent --lines 50
```

解析 metric，对照 loop-policy.md 判定 keep / discard / crash。

### 2.7 数据流总览

```
control: run build → wait → run server → wait → run client → wait → read → decide
build:   [===== 编译 + 打包 ~5min =====]
server:                          [== server 启动 ~30s ==]
client:                                               [=== bench ===]
```

---

## Phase 3：Terminate

全部 hypothesis 跑完或触发终止条件（`round >= max_rounds` / `total_duration >= max_duration_minutes` / `no_improvement_streak >= 3`）：

1. 停 server：`herdr pane run "$SERVER_PANE" "pkill CarlaUnreal"`
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

## Controller 时间利用

build 是最慢步骤（~5min）。controller 在这段时间内并行完成 bench 准备，不空转：

```
[启动 build] → [写 bench(1min)] → [定 marker(10s)] → [预分析下一个假设] → [等编译完成] → [秒接 server]
```

## 依赖

- **herdr** — 执行层引擎，必须 `HERDR_ENV=1`，并从 live JSON 解析 CarlaUE5 workspace/panes
- **本地规则与 gates** — `references/` 和 `scripts/` 提供 safety、benchmark、loop-policy 与状态检查
- **CARLA toolchain** — `package_fast.sh`、`CarlaUnreal.sh`、Python API
