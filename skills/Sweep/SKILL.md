---
name: Sweep
description: |
  Supervised automation loop for iterative code optimization with
  benchmark feedback. Originally designed for CARLA sensor performance,
  but applies to any compile→benchmark→analyze→improve loop.
  Use this skill whenever the user wants to run an automated optimization
  benchmark loop, iterate on code optimizations automatically, or set up
  a self-driving performance tuning workflow. Also trigger when the user
  mentions "autoresearch loop", "automatic benchmark", "optimization loop",
  "run experiments automatically", "自动优化", "自动跑 benchmark", or
  wants AI to generate and test optimization hypotheses without manual
  intervention for each build/benchmark cycle.
---

# Autoresearch Loop

compile→benchmark→analyze→improve loop。AI 驱动假设生成+打补丁+构建+基准测试+keep/discard 判定的自动化优化管道。

## 硬规则

**进入 patch/build/benchmark 前必须读取对应 reference：**
- 改代码前 → `references/safety-guardrails.md`
- 跑 benchmark 前 → `references/benchmark-contract.md`
- 决策 keep/discard 前 → `references/loop-policy.md`

## 架构

两层分离：
- **AI 层（此 skill）**：代码分析、假设生成、patch 应用、决策
- **机械层（`loop.py`）**：状态持久化、构建执行、benchmark 启动/poll、结果比较

状态文件：`.agent-state/autoresearch-loop-state.yaml`，proposal 压缩后仍可恢复。

## 状态机

```
[INIT] → [ANALYZING] → [PATCHING] → [BUILDING] → [BENCHMARKING] → [DECIDING]
                ↑                                                          |
                |◄──────── revert + next hypothesis (discard/crash) ──────┤
                |◄──────── update baseline + next hypothesis (keep) ──────┤
                                                                          ▼
                                                                   [TERMINATED]
```

## Phase 1: Initialize

**第一步：pre-flight gate。** 在碰任何代码之前。

```bash
python3 ~/.claude/skills/Sweep/scripts/preflight_gate.py
```

blocked → 停止，修复后重跑。pass → 继续。

1. 无 baseline → 手动跑一次 baseline experiment（见 `references/benchmark-contract.md`）
2. `loop init`：指定 target、metric、dimensions、max_rounds、max_duration、baseline
3. 分析 codebase，生成 hypothesis queue → `loop add-hypotheses`

## Phase 2: Loop Execution

对每个 pending hypothesis 执行状态机。

**每轮开始跑 round gate**：
```bash
python3 ~/.claude/skills/Sweep/scripts/round_gate.py
```
blocked → 停止 loop，报告。pass → 继续。改代码前读 `references/safety-guardrails.md`。

### Patch → Build → Benchmark → Decide

- **Patch**：读 target file，apply optimization，commit with hypothesis ID
- **Build**：`loop build` 构建，失败 → crash + revert
- **Benchmark**：`loop benchmark-launch` → ScheduleWakeup poll → `loop benchmark-poll`
- **Decide**：`loop decide` 判定 keep/discard。策略见 `references/loop-policy.md`

### Termination Check

每轮后跑 `loop status`。终止条件：`round >= max_rounds` / `total_duration >= max_duration_minutes` / `no_improvement_streak >= 3`。

## Phase 3: Terminate

- 打印最终摘要：best latency、commit、round、counts
- best 为非 baseline commit → 提醒用户 push/save
- Canon promotion：创建 update card，更新 Canon task/project/pattern/incident
- 不自动 push/merge

## State Persistence

Key fields in `.agent-state/autoresearch-loop-state.yaml`:

| Field | Description |
|-------|-------------|
| `loop_id` | Unique loop instance ID |
| `state` | Current state machine state |
| `config` | Optimization configuration |
| `baseline` | Current baseline metrics + commit |
| `best` | Best result found |
| `current` | Current round, hypothesis, workspace paths |
| `hypotheses` | Hypothesis queue with status |
| `termination` | Streak counters, termination reason |

State 丢失或损坏 → 必须从头重新初始化。

## Error Handling

| Scenario | Action |
|----------|--------|
| Build failure | Mark crash, revert, next |
| Server fails to start | External runner reports failure, revert, next |
| Benchmark crash | External runner reports failure, revert, next |
| Point count mismatch | Discard, revert, next |
| Patch apply failure | Log, skip hypothesis |
| All hypotheses tested | Terminate with current best |

## 资源

- `references/safety-guardrails.md` — 硬规则：patch/build/benchmark 前必读
- `references/benchmark-contract.md` — Metrics 格式、benchmark 执行协议、decide contract
- `references/loop-policy.md` — Hypothesis queue、keep/discard/crash 判定、termination、Canon
