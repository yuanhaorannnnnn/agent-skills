# Engage — 接敌开发

## 预检

1. 确认方案已通过线下评审
2. 确认 `state.json` 中 `phase: review`，`design_doc_path` 非空

## 执行

### Step 1: 变更需求单状态

用 yunxiao MCP 将需求单状态改为 `开发中`。

### Step 2: 提取开发任务

读取 CONOPS 方案文档（`state.json` 中的 `design_doc_path`），提取开发任务列表：
- 需要实现的接口/模块
- 需要修改的配置/参数
- 需要更新的文档

### Step 3: 创建规划工作区

调用 Staging skill 创建 `.planning/conversations/<demand-id>/` 工作区：
- `task_plan.md` — 从 Step 2 的任务列表初始化
- `findings.md` — 空模板
- `progress.md` — 空模板

### Step 4: 生成开发目标

将 Step 2 的任务列表 + 方案关键约束 + 接口定义，生成为 `goal.md`（放在 planning 工作区或 CI 可读的位置）。goal.md 是结构化开发摘要：

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
```

### Step 5: 启动开发

运行 `/goal` 读取 `goal.md`，启动开发流程。

开发流程自动衔接：
```
/goal → TDD（隐式触发）→ 编码 → code-review → Traceback
```

Traceback 完成后停止——需手动编译验证，通过后手动运行 Sanitize 收尾。

## 更新 state.json

```json
{
  "phase": "review → dev"
}
```

## 完成检查

- [ ] 需求单状态已改为 `开发中`
- [ ] 开发任务已从方案中提取
- [ ] `.planning/conversations/<demand-id>/` 工作区已创建
- [ ] `goal.md` 已生成
- [ ] `/goal` 已启动
- [ ] state.json 已更新
