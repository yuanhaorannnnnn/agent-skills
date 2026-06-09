---
name: Execute
description: |
  Natural language task → runtime goal.md + Canon task page → launch execution.
  Use when the user wants to start a coding task without a demand/bug ID — says
  开动、执行、帮我实现、写一个、帮我改、做出来、开始写、implement this、
  build this、add this feature. Reads code context, derives structured tasks,
  writes a repo-local goal.md execution brief, records durable state in Canon,
  and launches /goal (or Pi /loop custom) with goal.md.

  Supports --plan for complex multi-phase tasks: loads plan-template from
  references/plan-template.md, writes § Plan / § Findings / § Progress into the
  Canon task page, generates goal.md from that task context, and launches /goal.

  Do NOT use when the user works with a known demand/bug ID — Tasking or
  Repair handle those. Do NOT use for questions, code review, or research.
---

# Execute — 火力任务

用户一句话 → goal.md + Canon task page → /goal。

## Hard Rule

When the user invokes `$Execute`, do not implement inline before `/goal` is actually triggered. First generate or update `goal.md`, create or update the Canon task page, then trigger or hand off:

```text
/goal <absolute-goal-md-path>
```

If the current agent cannot directly inject the runtime slash command, stop after preparing `goal.md` and report the exact `/goal` command for the user to run. Do not continue implementation inline and do not claim `/goal` was launched.

## 参数

| 参数 | 作用 |
|------|------|
| (无参数) | 标准模式：从用户描述生成 `goal.md`，并创建新 Canon task page |
| `--plan` | 计划模式：额外加载 plan-template，写入 § Plan / § Findings / § Progress |
| `<task-page-path>` | 传入已有 Canon task page 路径（如 `/media/yhr/2T/Canon/tasks/JHBN-7679.md`），更新该 task page 并从中生成 `goal.md` |

当 `--plan` 和 `<task-page-path>` 同时传入时（如 `Execute --plan /media/yhr/2T/Canon/tasks/JHBN-7679.md`），plan 写入已有 task page，不新建；随后生成 repo-local `goal.md` 并触发 `/goal <goal.md>`。Tasking Engage 使用此模式。

## 流程

### Step 1: 感知战场

快速扫描当前上下文——不是深度分析：

- 当前项目、语言、仓库根目录
- 最近修改的文件（`git diff --stat HEAD` 或未提交改动）
- 任务描述中提到或涉及到的模块名/接口名
- Canon 相关决策或约束（`rg` /media/yhr/2T/Canon/decisions/ 和 patterns/）

### Step 2: 编写执行目标

基于用户描述 + Step 1 的代码上下文，用以下模板输出结构化目标，写入 repo-local `goal.md`。同时把摘要同步到 Canon task page § Goal。

```markdown
# <任务标题>

## 目标
[一段话描述核心功能]

## 任务清单
- [ ] <task1>
- [ ] <task2>

## 关键约束
- <constraint1>
- <constraint2>

## 接口影响
[涉及的函数签名/参数变更，如无则写"无"]
```

### Step 2b: --plan 模式（可选）

如果传了 `--plan`，加载 `references/plan-template.md`，在 Canon task page 中写入：

- **§ Plan** — 5-phase 结构（Discovery → Planning → Implementation → Testing → Delivery），含 phase checklist、architecture decisions 表、validation 命令
- **§ Findings** — Requirements / Code Observations / Research Findings / Open Questions / Resources
- **§ Progress** — Session log + Test Results + Handoff Notes

task page 已有对应 section 时合并更新，不覆盖。

### Step 3: 落盘 goal.md + Canon

解析 `<task-slug>`：从已有 task page 文件名或任务标题生成。默认写入当前 repo：

```text
<repo-root>/.proposal/<task-slug>/goal.md
```

如果传入 `<task-page-path>`，更新该 Canon task page；否则按 slug 规则创建新路径：

```text
/media/yhr/2T/Canon/tasks/<task-slug>.md
```

Canon task page 记录 durable state：Goal / Tasks / Plan / Findings / Progress / Artifacts，并在 § Artifacts 或 frontmatter `artifacts` 引用 `goal_path`。

`goal.md` 是 runtime execution brief；Canon task page 是 durable task state。不要把 Canon task page 直接传给 `/goal`。

### Step 4: 启动执行

解析最终 `goal.md` 绝对路径：

```text
<repo-root>/.proposal/<task-slug>/goal.md
```

Codex 和 Claude Code 都内置 `/goal`，必须真实触发 runtime slash command：

```text
/goal <absolute-goal-md-path>
```

示例：

```text
/goal /media/yhr/2T/CarlaUE5/.proposal/JHBN-7712/goal.md
```

`/goal` 的唯一参数是 `goal.md` 的绝对路径。不要把“当前 agent 继续手动执行”伪装成已启动 `/goal`；如果 slash command 触发失败，报告失败原因并停止，不做 inline 替代。

Pi runtime 使用：

```text
/loop custom <absolute-goal-md-path>
```

触发后，agent 读取 `goal.md` 执行；Canon task page 用于持久记录进度、证据和回写结果。

**Step 4 后跑 gate**：
```bash
python3 ~/.claude/skills/Execute/scripts/execution_gate.py --goal <goal-md> --task <canon-task-path>
```
blocked → goal.md 缺失或 Canon task page 未更新。pass → /goal 已准备好。

### Step 5: Review Gate

实现完成后、Traceback/Sanitize 前，读取共享质量门：

```text
/home/yhr/.agents/repos/agent-skills/references/review-gate.md
```

用 Canon task page、`goal.md`、当前 diff、测试/构建证据执行 review。有 blocker 时先修复；无 blocker 时把结果写入 Canon task page § Findings / § Evidence / § Timeline。


## Workflow Gate Contract

Execute must satisfy the shared workflow output contract:

```text
/home/yhr/.agents/repos/agent-skills/references/skill-output-contract.md
```

`goal.md` is the runtime execution brief; the Canon task page is durable state. A downstream agent must be able to resume from those two files plus linked artifacts.

## Gotchas

- `$Execute` does not mean “start coding now”. It means prepare `goal.md` + Canon task page, then trigger or hand off `/goal <goal.md>`.
- Do not pass the Canon task page to `/goal`; pass the repo-local `goal.md` absolute path.
- If the runtime cannot inject `/goal`, stop after writing files and report the exact command. Do not continue inline as a substitute.
- `--plan <task-page-path>` updates the existing Canon task page; it must not create a duplicate task page under a similar slug.
- Review Gate runs after implementation and before Traceback/Sanitize; blockers stop delivery.

## 与其他 skill 的关系

```
Tasking Engage → Execute --plan（生成 goal.md，接管原 Staging 的 workspace 创建职责）
Repair Fix    → 默认不走 Execute；使用 fix_plan.md + Neutralize
用户直接调用  → Execute [--plan]（workflow 外的开发启动入口）
```
