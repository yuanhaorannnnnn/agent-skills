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

### 模式识别与建议

- `auto` 只选择执行者；`local/task` 决定是否用 Canon 持久跟踪。复杂任务可以是 `direct + task`，不因耗时或文件数自动升级模式。
- 普通规划按需进行，优先复用已有方案、任务清单和验证安排；它不等于 `--plan`。当前 `--plan` 隐含 `--goal`，不能仅因需要拆阶段而自动启用。
- 当目标与验收已明确、预计需要跨轮次调查/验证，且持续续接能减少无必要的人工催促时，主动建议 Goal：简述目标、验收、运行边界及预期收益；若已有计划则复用，不另造文件。一次说明足够，不在每轮重复建议。
- 实际任务存在值得用户决定的模式分叉时，优先使用当前 runtime 可用的结构化提问工具（如 AskUserQuestion 或可用的 request_user_input 变体），给出 2–3 个适用选项；推荐项置首并标“推荐”，说明推荐依据及各项的实际收益/代价。按本轮操作与已有计划判断，不按大任务标题或历史规模选模式。通常比较“保持普通执行”“启用 Goal”，只有同时需要新增持久计划时才加入“Plan + Goal”；明确后者也会启用持续目标。不得提供当前 runtime 不支持的启动能力，不绕过工具的模式/权限限制；无可用提问工具时用普通文本给出同样选择。
- 这不是每次 execute 的必经问卷。已有明确模式选择时直接遵循；只有新证据改变取舍才重新提问。预选推荐项、无回答或超时均不等于选择；未明确选择 Goal/Plan 时只继续原授权工作。用户明确选择且满足 runtime 启动条件后直接实施，不再重复确认。
- `--goal` / `--plan` 保留显式调用；用户以自然语言明确要求启用持续目标也可作为启动请求。仅要求“完成任务”或一次“继续”不等于要求启动 Goal。遵守当前 runtime 的启动条件；明确请求已存在时不重复索取确认，无法启动则提供准确 handoff。
- 建议未获采纳时继续已授权的普通执行；不要等待用户选择模式才开始工作，不恢复暂停任务。目标或验收尚不清楚、外部输入不可得时，先解决这些问题，不能用 Goal 替代判断或消除真实阻塞。
- 遥测记录实际使用的模式，提出建议不记为 `goal/plan` 已启动；零记录或路由比例不作为增加委托、计划或目标的配额。

可选参数：

- `<task-page-path>`：复用明确的 Canon task page。
- `--designer <model>`：仅与 `--delegate` 一起使用，让指定模型先产出执行 brief。
- `--executor <model>`：指定执行模型或系列；仍须满足下述最新可调用版本规则。

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

成功条件描述完成时必须成立的结果及其证据，不能只列“改代码、跑测试、写报告”等动作。探索可以用证据回答明确问题并得到否定或有限结论，但不能将“做完分析”当成原交付目标完成。沿用已批准的验收范围，不为显得完整追加未授权的构建或实验。

调查、调优和多轮验证按以下原则推进；普通机械操作不逐步写分析，不新增固定表单或平行报告，持久任务复用 Current State / Next Step / Progress：

- **每轮的判别价值：**开始有实质成本的尝试前，明确当前假设、预期会看到的结果，以及哪种观测能区分候选解释；优先选择在授权范围内能推进交付或改变下一步判断的行动，不追求无关信息。结束后把观测与推断分开，重点检查实际与预期的差异，说明哪些判断增强、削弱或失效，距目标还差什么、下一步为何值得做。没有事前预测时明确为事后解释，不补写成已验证预测；环境失败、无效输入或不可比较结果不能充当假设的反证。无新证据就如实说明；发现新变量可以扩大不确定性，不硬编收获或强行收敛。
- **保留可比较性：**对照实验记录必要的输入、版本、环境与状态差异；失败运行遗留物或同时改变多个条件会削弱归因。依赖比较的下一轮应恢复可比基线，或明确哪些差异尚未排除。重试须有可说明的理由（如暂时故障或需重复采样）；连续无新信息时重新审视假设、观测方法或前置条件，不机械重跑，也不据单次成功宣布根因成立。选数据、观测代理或搜索参数时遵循既有 research-admission。
- **分清终止原因：**完成、真实阻塞、达到已约定投入边界分别报告，保留已完成证据和剩余项。长任务沿用用户/runtime 的预算或已批准实验范围；下一步显著增加投入时带具体收益与代价回来决定，不擅自扩大预算，也不自设轮数上限提前结束已授权任务。预算用尽不等于完成；状态变更遵守 runtime，不能自行用 paused/blocked 绕过其条件。
- **逐项核验主张：**交付包含不同层级的主张时，分别映射证据和适用范围，例如机制实现、参考输出一致、性能达标、真实设备吻合；区分已验证、失败、未运行和证据不足。静态通过不能替代运行通过，局部测试不能外推整体；小任务用短说明即可，只有复杂验收才需矩阵。

执行中按全局协作规则同步共同判断，提供足以支持下一步决策的增量信息与最小证据；结果、偏离和剩余差距连同其决策影响一起说明，不用测试通过数量替代整体位置判断。持久任务的 Current State 保存最新判断及适用边界，Progress 保留关键修正及证据，Next Step 指向下一项有判别价值或交付价值的行动。前提失效则停止依赖它的工作；授权内调整继续推进，需要改目标、验收或显著追加投入时才请求缺失的决定，保留用户批准依据，不以重写计划掩盖未交付项。

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

没有满足全部规约的候选时，`auto` 解析为 `direct`；显式 `--delegate` 或不合规的显式模型指定记录 blocker，不以内联执行或旧版本替代委托。

下游 agent 的 `auto` 必须解析为 `direct`，不得再次组队。默认最大 delegation depth 是 1；已在 depth 1 的 agent 不得使用 `--delegate`。主 agent 保留任务 owner、复核责任和 Canon 写回责任。

#### 委托模型选择规约

以下规则适用于 `auto` 选择的委托及显式 `--delegate`，同时约束 `--executor` 和 `--designer`：

1. **确认实际可用性**：从运行时元数据确认可调用模型池、实际 model ID 和别名映射；不能从默认配置、模型自述或旧记录猜测可用性。
2. **每个系列只保留最新版**：Sol、Luna 等同一系列，永远只选当前模型池中的最新可调用版本。新旧关系优先采用运行时说明；版本号可比较时按数值比较，不按字符串排序。无法确认最新版本的系列不进入候选池，不硬编码“最新版”ID。
3. **自由选择模型**：允许 Astra、与主 agent 相同的模型及其他系列，不设模型等级、代际或 provider 白名单。跨 provider 可使用已接入且可调用的工具；实际可用性与任务授权仍须满足。
4. **核对显式选择**：系列名解析为该系列最新版；显式版本也必须是最新且可调用。不符合时说明原因，不静默升级、降级或替换用户指定模型。

例如运行时同时提供 `gpt-6.1-sol`、`gpt-6-sol`，Sol 候选只保留前者；主模型也是 `gpt-6.1-sol` 时，仍可委托该模型。示例版本不是固定配置。

在 Routing 的 `models` 与 `evidence` 记录选中模型的实际 ID 及模型池/最新版判断依据；派发及复用旧 agent 前核对最终实际模型，包括默认继承的模型。

#### `--direct`：强制当前 agent

当前 agent 实现并验证；持久路径回写 Canon。Local direct 在当前回复交付，不创建 `goal.md`。

#### `--delegate`：强制轻量委托

主 agent 使用 runtime 的子代理能力传递执行契约；runtime 不支持时记录 blocker 并明确报告，不能把 inline 执行伪装成委托。executor / designer 必须满足“委托模型选择规约”，从各系列最新版中选择合格候选；没有候选时保持 blocker，不以内联或旧版本兜底。

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
