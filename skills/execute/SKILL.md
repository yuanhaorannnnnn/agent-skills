---
name: execute
description: |
  执行具体任务并在 Canon task page 留下可恢复记录。用户说“执行”“开始做”“开动”
  “落实”“实施”“修改”“修复”“处理这个任务”“帮我做”“委托执行”“交给其他模型”，
  或显式调用 $execute / /execute 时使用。默认自动选择当前 agent 或一层委托；--direct
  和 --delegate 强制覆盖。--goal 创建 goal.md；--plan 创建详细计划并隐含 --goal。普通问答、
  解释、只读 review、单纯调研不触发；已知需求/缺陷 ID 分别由 tasking/repair 管理。
---

# execute — 任务执行入口

统一承接普通任务执行、轻量委托和持久 goal。所有路径创建或更新 Canon task；执行者路由与持久化深度正交。

## 参数与模式

| 维度 | 默认 | 覆盖 | 作用 |
|---|---|---|---|
| 执行者 | `auto` | `--direct` / `--delegate` | 自动路由、强制当前 agent、强制一层委托 |
| 持久化 | 无 | `--goal` / `--plan` | 无 `goal.md`、创建 runtime brief、增加 Canon Plan 并隐含 `--goal` |

因此 `execute`、`execute --direct`、`execute --delegate`、`execute --plan --delegate` 都合法；`--direct` 与 `--delegate` 互斥。`--plan` 优先于显式 `--goal`。

可选参数：

- `<task-page-path>`：复用明确的 Canon task page。
- `--designer <model>`：仅与 `--delegate` 一起使用，让指定模型先产出执行 brief。
- `--executor <model>`：指定执行模型；未指定时按任务和 runtime 可用模型选择。

## 触发边界

以下中文表达应触发普通执行：执行、开始做、开动、落实、实施、修改、改一下、修复、处理这个任务、帮我做、按这个方案做。出现“委托、交给其他模型、指定模型执行、让 Terra/Luna 做”时选择 `--delegate`。

不用于纯问答、概念解释、只读诊断/review、单纯调研或用户明确说“先不动手”。已知 demand/bug ID 继续由 `tasking`/`repair` 持有生命周期；它们可调用本 skill，但 execute 不接管其状态、分支或 task identity。

## 共同流程

### 1. 解析任务与 Canon task

读取当前 repo、dirty baseline、用户约束和相关 Canon 页面。按 `<skills-root>/references/canon-task-resolution.md` 解析或创建一个 Canon task page。所有模式在修改代码或委托前写入：

- `## Goal`、`## Current State`、`## Next Step`、`## Key Decisions`
- `## Tasks`、`## Progress`、`## Artifacts`
- frontmatter 的 `workflows: [execute]`、`report_scope`、`weekly`、日期

轻量模式只写足以恢复任务的摘要，不创建 `.proposal` 文件。完成后更新任务状态、checklist、验证证据和时间线。

### 2. 形成执行契约与路由记录

执行契约至少包含：目标、非目标、scoped files、既有 dirty baseline、关键约束、可观察成功条件、验证命令。小任务可直接存在 Canon task；`--goal`/`--plan` 再把它压缩成 runtime brief。

在选择执行者后，所有模式必须写入 `## Routing`：

```markdown
## Routing
- routing_mode: auto | direct | delegate
- resolved_route: direct | delegate
- reason: <收益、上下文或显式覆盖理由>
- router_owner: main Execute router
- delegation_depth: 0 | 1
- downstream_auto_delegate: forbidden
- models: <current model and any designer/executor>
- scope: <delegated or local scope>
- status: <active | blocked | returned | verified>
- evidence: <brief, diff, test, or handoff reference>
```

reasoning effort 仅是路由信号，可影响“是否拆分”和模型选择；它不是执行 owner，也不绕过这份记录。

### 3. 选择执行路径

#### `auto`：默认路由

仅主/main agent 可在形成契约后自动选择：任务可独立拆分、下游能获得完整 scope/验收条件、委托收益超过交接成本且主 agent 可复核时，解析为 `delegate`；否则解析为 `direct`。小改动、强上下文依赖、频繁用户交互、不可独立验收的任务保持 direct。

需要委托时，executor 从当前 active provider 实际暴露、可调用的子代理模型池中选择；不要仅因某模型被认为“低级”而委托。active provider 为 `gpt` 时，候选范围限定为运行时可用的 GPT-6 模型，并排除 Astra（`gpt-6-astra`）。此限制同样适用于委托时显式指定的 `--executor` 和 `--designer`：模型不可用或超出范围时，不得静默替换为其他 provider 或 Astra。其他 provider 只使用其运行时实际暴露的模型，不推断跨 provider fallback。

若没有符合当前 provider/model 范围的委托模型，`auto` 解析为 `direct`；显式 `--delegate` 或不合范围的显式模型指定记录 blocker，不以内联执行或越界模型替代委托。

下游 agent 的 `auto` 必须解析为 `direct`，不得再次组队。默认最大 delegation depth 是 1；已在 depth 1 的 agent 不得使用 `--delegate`。主 agent 保留任务 owner、复核责任和 Canon 写回责任。

#### `--direct`：强制当前 agent

当前 agent 实现、验证并回写 Canon。不创建 `goal.md`，除非同时传 `--goal` 或 `--plan`。

#### `--delegate`：强制轻量委托

主 agent 使用 runtime 的子代理能力传递执行契约；runtime 不支持时记录 blocker 并明确报告，不能把 inline 执行伪装成委托。按任务需求和当前 provider 的可用模型选择 executor；当 active provider 为 `gpt` 时只从 GPT-6 模型中选择并排除 Astra，不再按“向低级模型委托”排序。显式模型必须符合该 provider/model 范围。

在 `## Delegation` 记录 executor、scope、status、evidence（以及可选 designer）。主 agent 复核下游 diff、测试和完成条件后才可标记完成。

#### `--goal` / `--plan`：持久化维度

`--goal` 创建 `<repo-root>/.proposal/<task-slug>/goal.md`，包含目标、任务清单、关键约束、接口影响、Observable Target、Module Boundary，并把绝对路径写入 Canon artifacts。用 `/goal <absolute-goal-md-path>`（Pi 使用 `/loop custom <path>`）启动；无法注入命令时返回准确 handoff，不以内联执行伪装已启动。

`--plan` 先读取 `references/plan-template.md`，合并更新 Canon 的 `## Plan`、`## Findings`、`## Progress`，再创建并启动 `goal.md`。已有 section 按 task-resolution merge contract 更新，不覆盖历史。

### 4. Gate 与 review

按持久化和路由维度运行 gate：

```bash
python3 <skill-dir>/scripts/execution_gate.py --mode none --route auto --task <canon-task>
python3 <skill-dir>/scripts/execution_gate.py --mode none --direct --task <canon-task>
python3 <skill-dir>/scripts/execution_gate.py --mode goal --delegate --task <canon-task> --goal <goal-md>
python3 <skill-dir>/scripts/execution_gate.py --mode plan --route auto --task <canon-task> --goal <goal-md>
```

代码或配置修改后，读取 `<skills-root>/references/review-gate.md`，以 task page、当前 diff 和验证证据 review；blocker 未解除不得宣称完成。

## 调用方约束

- `tasking Engage` → `execute --plan <existing-task-page>`；tasking 仍是 phase/state owner。
- `repair Fix` 默认不走 execute，继续使用自己的 `fix_plan` 与 gate。
- 其他 orchestrator 必须传入既有 task page，并保留自己的生命周期所有权。

## 输出契约

遵守 `<skills-root>/references/skill-output-contract.md` 与 `<skills-root>/references/canon-output-contract.md`。最终至少返回：`task_path`、持久化模式、`routing_mode`、`resolved_route`、执行者/委托状态、验证结果；只有 goal/plan 模式返回 `goal_path`。
