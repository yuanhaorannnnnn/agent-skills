# Engage — 接敌开发

## 预检

**第一步：读 gate。在改状态或启动开发之前。**

```bash
cat .proposal/<demand-id>/briefing_gate.json
```

| gate verdict | 行为 |
|-------------|------|
| **pass** | 正常进入 Engage |
| **ready** | 提示用户"方案评审是否已通过？"——等待用户下令 |
| **blocked** | **拒绝启动。** 列出缺失项，提示"回 Briefing 补"，停止 |

gate 通过后继续：

1. 确认 `state.json` 中 `phase: review`，`design_doc_path` 非空

## 执行

### Step 1: 变更需求单状态

1. 用 yunxiao MCP `get_work_item_workflow` 查询需求单的工作流，获取 `开发中` 对应的 status ID
2. 用 yunxiao MCP `update_work_item` 将需求单状态改为该 ID

**不要直接传中文状态名**——yunxiao API 只接受 status ID，传中文名会 400。

### Step 2: 提取开发任务

读取 CONOPS 方案文档（`state.json` 中的 `design_doc_path`），提取开发任务列表：
- 需要实现的接口/模块
- 需要修改的配置/参数
- 需要更新的文档

### Step 3: 生成 Canon 计划和 goal.md

调用 `Execute --plan /media/yhr/2T/Canon/tasks/<demand-id>.md`：
- 更新 Canon task page § Plan / § Findings / § Progress
- 生成 repo-local `goal.md`: `<repo-root>/.proposal/<demand-id>/goal.md`
- `goal.md` 是 `/goal` 的 runtime 输入；Canon task page 是 durable state
- 把 Step 2 的任务列表、方案约束、observable target 和受影响 module boundary 作为输入

不再创建 `.planning/conversations/<demand-id>/` 工作区；Canon task page 承载计划，`goal.md` 承载 runtime 执行目标。Tasking 仍是需求 phase/state owner；Execute 不修改 Yunxiao、`state.json.phase`、需求分支或 task identity。

### Step 4: 校验 Execute 输出

读取 Execute 生成的 `<repo-root>/.proposal/<demand-id>/goal.md`，确认它包含 Step 2 的任务列表、方案关键约束、接口定义、observable target 和 module boundary。缺项时退回 Execute 补齐，不由 Tasking 重写第二份目标。

校验通过后，将 `goal.md` 路径写入 `state.json.goal_path`，将 Canon task page 路径写入 `state.json.canon_task_path`。

```markdown
# <需求标题>
## 目标
[一段话描述本次开发要实现的核心功能]
## 任务清单
- [ ] 任务 1
- [ ] 任务 2
## 关键约束
- 约束 1
- 约束 2
## 接口定义摘要
[从 CONOPS 方案提取的接口签名/参数]
## Observable Target
[修改前证据、成功判据、验证命令]
## Module Boundary
[受影响模块、public interface、预期扩大/保持/收敛]
```

### Step 5: 启动开发

以 `goal.md` 路径作为 runtime execution brief 启动开发：

| Runtime | Command |
|---------|---------|
| Codex | `/goal <repo-root>/.proposal/<demand-id>/goal.md` |
| Claude Code | `/goal <repo-root>/.proposal/<demand-id>/goal.md` |
| Pi | `/loop custom <repo-root>/.proposal/<demand-id>/goal.md` |

`/goal` 和 `/loop custom` 都是 agent runtime 的 slash commands，不是 shell commands。对应 runtime 必须真实触发命令；不要把“当前 agent 继续手动执行”伪装成已启动。

如果当前 agent 无法主动注入 slash command，向用户报告 `goal.md` 路径和可复制命令，停止在“等待用户触发 runtime command”状态。只有当前 runtime 确实没有等价执行命令时，才停止在“开发目标已准备好”状态。

开发流程自动衔接：
```
/goal <goal_path> 或 /loop custom <goal_path> → observable-target feedback loop → 编码 → Review Gate → Traceback
```

实现完成后先读取共享质量门：

```text
/home/yhr/.agents/repos/agent-skills/references/review-gate.md
```

用 Canon task page、`goal.md`、方案文档、当前 diff、测试/编译证据做 review。有 blocker 时停在 Engage，不进入 Traceback/Sanitize；无 blocker 时把 review 结果写入 Canon task page § Findings / § Evidence / § Timeline，再运行 Traceback。

Traceback 完成后运行机器 gate：

    python3 <skills-root>/Traceback/scripts/traceback_gate.py \
      --dir .planning/<demand-id> --repo <repo-root> --json

'pass' 或有 Canon skip reason 的 'skipped' 才能进入 Engage gate。随后停止——需手动编译验证，通过后手动运行 Sanitize 收尾。

### Canon promotion

- `.planning/conversations/<demand-id>/` 不再创建；`goal.md` 是 runtime execution brief，Canon task page 是 durable state。
- 更新 Canon task page：记录开发任务摘要、关键约束、review 结果、状态 `dev` 和下一步验证/Turnover 条件。
- 创建 update card：`/media/yhr/2T/Canon/raw/update-cards/<date>-tasking-<demand-id>-engage.md`，把 Canon task page 和 `goal.md` 路径作为 artifact refs。

## 更新 state.json

```json
{
  "phase": "review → dev",
  "goal_path": "<repo-root>/.proposal/<demand-id>/goal.md",
  "canon_task_path": "/media/yhr/2T/Canon/tasks/<demand-id>.md"
}
```

## 完成检查

Engage 完成跑 gate 脚本：

```bash
python3 <skill-dir>/scripts/engage_gate.py <demand-id> --repo <repo-root> --json
```

输出 'engage_gate.json'。Engage 无 human gate——全部 machine check：state phase、goal.md 存在、Review Gate 通过、当前 workspace 的 'traceback-gate.json' 为 'pass|skipped'、Canon 更新。不要读取 'state.json.traceback_done'。
