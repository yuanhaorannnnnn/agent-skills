---
name: execute
description: |
  执行具体任务；按风险和恢复需求决定是否写 Canon task。触发于"执行"、"开始做"、"落实"、"实施"、"修改"、"修复"、"帮我做"、"委托执行"或 $execute。普通问答、只读审阅、单纯调研不触发；已知需求/缺陷 ID 由 tasking/repair 管理。
---

# execute — 任务执行入口

统一承接普通任务执行、轻量委托和持久 goal。可恢复的工作写 Canon task；局部、可逆的单仓库 direct 修改可留在当前对话。执行者路由与持久化深度正交。

## 参数与模式

| 维度 | 默认 | 覆盖 | 作用 |
|---|---|---|---|
| 执行者 | `auto` | `--direct` / `--delegate` | 自动路由、强制当前 agent、强制一层委托 |
| 持久化 | 按任务风险 | `--goal` / `--plan` | 局部 direct 可不建 task；持久路径创建 Canon task；`--goal` 创建 runtime brief；`--plan` 增加 Canon Plan 并隐含 `--goal` |

因此 `execute`、`execute --direct`、`execute --delegate`、`execute --plan --delegate` 都合法；`--direct` 与 `--delegate` 互斥。`--plan` 优先于显式 `--goal`。

可选参数：

- `<task-page-path>`：复用明确的 Canon task page。
- `--designer <model>`：仅与 `--delegate` 一起使用，让指定模型先产出执行 brief。
- `--executor <model>`：指定执行模型或系列；仍须满足下述最新版本及异模型约束。

## 触发边界

以下中文表达应触发普通执行：执行、开始做、开动、落实、实施、修改、改一下、修复、处理这个任务、帮我做、按这个方案做。出现“委托、交给其他模型、指定模型执行、让 Terra/Luna 做”时选择 `--delegate`。

不用于纯问答、概念解释、只读诊断/review、单纯调研或用户明确说“先不动手”。已知 demand/bug ID 继续由 `tasking`/`repair` 持有生命周期；它们可调用本 skill，但 execute 不接管其状态、分支或 task identity。

## 共同流程

### 1. 判断是否需要 Canon task

先读用户约束、相关文件和 dirty baseline。仅当任务是**单仓库、局部、可逆、当前对话内可完成的 direct 修改**，且没有直接关联的现有 Canon task、已批准的交付契约、委托、跨仓库依赖、公共接口或安全/数据边界变更、外部状态变更或明确的后续交接需求时，使用 local direct：不新建 Canon task，也不运行 `execution_gate.py`；完成后在当前回复列出改动和验证。

其他情况查询相关 Canon 页面，按 `<skills-root>/references/canon-task-resolution.md` 解析或创建 task page；修改代码或委托前写入：

- `## Goal`、`## Current State`、`## Next Step`、`## Key Decisions`
- `## Tasks`、`## Progress`、`## Artifacts`
- frontmatter 的 `workflows: [execute]`、`report_scope`、`weekly`、日期

持久路径只写足以恢复任务的摘要；`--goal`/`--plan` 才创建项目规则指定的 goal 文件。完成后更新任务状态、checklist、验证证据和时间线。

### 2. 形成执行契约与路由记录

持久路径的执行契约至少包含：目标、非目标、scoped files、既有 dirty baseline、关键约束、可观察成功条件、验证命令；`--goal`/`--plan` 再把它压缩成 runtime brief。Local direct 在当前对话保留目标、范围和验证结果。

在选择执行者后，持久路径写入 `## Routing`；local direct 无需单独记录：

```markdown
## Routing
- routing_mode: auto | direct | delegate
- resolved_route: direct | delegate
- reason: <收益、上下文或显式覆盖理由>
- router_owner: main Execute router
- delegation_depth: 0 | 1
- downstream_auto_delegate: forbidden
- models: <运行时确认的主模型及designer/executor实际model ID>
- scope: <delegated or local scope>
- status: <active | blocked | returned | verified>
- evidence: <brief, diff, test, or handoff reference>
```

reasoning effort 仅是路由信号，可影响“是否拆分”和模型选择；它不是执行 owner，也不绕过这份记录。

### 3. 选择执行路径

#### `auto`：默认路由

仅主/main agent 可在形成契约后自动选择：任务可独立拆分、下游能获得完整 scope/验收条件、委托收益超过交接成本且主 agent 可复核时，解析为 `delegate`；否则解析为 `direct`。小改动、强上下文依赖、频繁用户交互、不可独立验收的任务保持 direct。

需要委托时，按下述“委托模型选择规约”选择 executor；不要仅因模型被认为“低级”而委托。

没有满足全部规约的候选时，`auto` 解析为 `direct`；显式 `--delegate` 或不合规的显式模型指定记录 blocker，不以内联执行、旧版本、同模型或跨 provider 替代委托。

下游 agent 的 `auto` 必须解析为 `direct`，不得再次组队。默认最大 delegation depth 是 1；已在 depth 1 的 agent 不得使用 `--delegate`。主 agent 保留任务 owner、复核责任和 Canon 写回责任。

#### 委托模型选择规约

以下规则适用于 `auto` 选择的委托及显式 `--delegate`，同时约束 `--executor` 和 `--designer`：

1. **确认实际模型池与主模型**：只使用当前 active provider 实际暴露、可调用的模型；从运行时元数据确认主模型的实际 model ID 和别名映射。不能从默认配置、模型自述或旧记录猜测。
2. **每个系列只保留最新版**：Sol、Luna 等同一系列，永远只选当前模型池中的最新可调用版本。先归并系列并选最新版，再做主模型排除；不得为避开主模型而退回同系列旧版。新旧关系优先采用运行时说明；版本号可比较时按数值比较，不按字符串排序。无法确认最新版本的系列不进入候选池，不硬编码“最新版”ID。
3. **排除同模型**：被委托的实际 model ID 不得与主模型相同。别名、reasoning effort 或 service tier 不同，都不算不同模型。主模型身份无法确认时，不派发委托。
4. **保留 provider 范围**：active provider 为 `gpt` 时，只允许 GPT-6 系列（含其小版本），排除整个 Astra 系列；其他 provider 只用其实际暴露的模型。不使用跨 provider fallback。最新版不合范围时，排除该系列，不回退旧版。
5. **核对显式选择**：系列名解析为该系列最新版；显式版本也必须是最新、可调用、合范围且不同于主模型。不合规时说明原因，不静默升级、降级或替换用户指定模型。

例如运行时同时提供 `gpt-6.1-sol`、`gpt-6-sol`，Sol候选只保留前者；若主模型也是 `gpt-6.1-sol`，整个Sol候选被排除，不能改委托旧版Sol。可选其他系列的最新版；没有合格模型时，按上面的 `auto` / `--delegate` 阻塞规则处理。示例版本不是固定配置。

在 Routing 的 `models` 与 `evidence` 记录主模型、选中模型的实际ID及模型池/最新版判断依据；派发前重新核对，不能只记录“Sol”或“继承主模型”。

#### `--direct`：强制当前 agent

当前 agent 实现并验证；持久路径回写 Canon。Local direct 在当前回复交付，不创建 `goal.md`。

#### `--delegate`：强制轻量委托

主 agent 使用 runtime 的子代理能力传递执行契约；runtime 不支持时记录 blocker 并明确报告，不能把 inline 执行伪装成委托。executor / designer 必须满足“委托模型选择规约”，从各系列最新版中选不同于主模型的合格候选；没有候选时保持 blocker，不以内联、同模型或旧版本兜底。

在 `## Delegation` 记录 executor、scope、status、evidence（以及可选 designer）。主 agent 复核下游 diff、测试和完成条件后才可标记完成。

#### `--goal` / `--plan`：持久化维度

`--goal` 先读取目标仓库 AGENTS.md 和文档布局规则。项目明确规定材料归仓路径时优先遵循，例如 CARLA 的 `Docs/guides/documentation.md` 指定 `<repo-root>/Docs/tasks/<task-slug>/goal.md`；没有项目规定时使用 `<repo-root>/.proposal/<task-slug>/goal.md`。创建该文件，包含目标、任务清单、关键约束、接口影响、Observable Target、Module Boundary，并把绝对路径写入 Canon artifacts。用 `/goal <absolute-goal-md-path>`（Pi 使用 `/loop custom <path>`）启动；无法注入命令时返回准确 handoff，不以内联执行伪装已启动。

`--plan` 先读取 `references/plan-template.md`，合并更新 Canon 的 `## Plan`、`## Findings`、`## Progress`，再创建并启动 `goal.md`。已有 section 按 task-resolution merge contract 更新，不覆盖历史。

### 4. Gate 与 review

持久路径按持久化和路由维度运行 gate；local direct 跳过此 task-file gate，仍运行与改动相关的验证：

```bash
python3 <skill-dir>/scripts/execution_gate.py --mode none --route auto --task <canon-task>
python3 <skill-dir>/scripts/execution_gate.py --mode none --direct --task <canon-task>
python3 <skill-dir>/scripts/execution_gate.py --mode goal --delegate --task <canon-task> --goal <goal-md>
python3 <skill-dir>/scripts/execution_gate.py --mode plan --route auto --task <canon-task> --goal <goal-md>
```

代码或配置修改后，读取 `<skills-root>/references/review-gate.md`，以当前 diff 和验证证据 review；持久路径再加入 task page。Blocker 未解除不得宣称完成。

## 调用方约束

- `tasking Engage` → `execute --plan <existing-task-page>`；tasking 仍是 phase/state owner。
- `repair Fix` 默认不走 execute，继续使用自己的 `fix_plan` 与 gate。
- 其他 orchestrator 必须传入既有 task page，并保留自己的生命周期所有权。

## 输出契约

遵守 `<skills-root>/references/skill-output-contract.md` 与 `<skills-root>/references/canon-output-contract.md`。Local direct 返回改动和验证结果；持久路径返回 `task_path`、持久化模式、`routing_mode`、`resolved_route`、执行者/委托状态、验证结果；只有 goal/plan 模式返回 `goal_path`。

## Routing telemetry

Emit one final local event following
[the shared routing contract](/home/yhr/.agents/repos/agent-skills/references/skill-telemetry.md).
Use actual executor `route=direct|delegate|unresolved`,
`requested=auto|direct|delegate`, `persistence=local|task|goal|plan`.
Explicit direct/delegate supplies `expected-route`; automatic choice leaves it
unset. Unsupported explicit delegation → `route=unresolved`, outcome `blocked`,
expected `delegate`; do not label inline work as delegation.
Record actual step states for `implementation`, `delegation`, `validation`,
`review`, `execution-gate`. Local direct → execution-gate `skipped`;
selected but undispatched delegation → `pending`. Pass requires verification,
including review of returned work. Attach task/gate refs when available.
