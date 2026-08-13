# Turnover — 任务移交

## 预检

**第一步：读 gate。在发评论或改状态之前。**

```bash
cat .proposal/<demand-id>/engage_gate.json
```

| gate verdict | 行为 |
|-------------|------|
| **pass** | 正常进入 Turnover |
| **blocked** | **拒绝启动。** 列出缺失项，提示"回 Engage 补"，停止 |

gate 通过后继续：

1. 确认编译验证已通过
2. 确认交付物链接已准备好（手动打包产生的 URL）
3. 确认 `state.json` 中 `phase: dev`

## 参数

```
/Tasking Turnover <demand-id> --deliverables "<url1> <url2> ..."
```

`--deliverables` 必传，支持空格分隔的多个 URL。

## 执行

### Step 1: 更新评论区

用 yunxiao MCP 在需求单评论区发布交付物清单：

```
交付物：
- <url1>
- <url2>
```

### Step 2: 变更需求单状态

1. 用 yunxiao MCP `get_work_item_workflow` 查询需求单的工作流，获取 `系统测试` 对应的 status ID
2. 用 yunxiao MCP `update_work_item` 将需求单状态改为该 ID

**不要直接传中文状态名**——yunxiao API 只接受 status ID，传中文名会 400。

### Step 3: 变更需求单负责人

1. 用 yunxiao MCP `search_organization_members` 按姓名 `樊亮亮` 查询 userId
2. 用 yunxiao MCP `update_work_item` 将 `assignedTo` 设为该 userId

**不要直接传中文名**——先解析为 userId 再更新。

### Step 4: Canon promotion

- 更新 Canon task page：记录状态 `test`、交付物 URL、系统测试负责人 `樊亮亮`、云效评论证据和后续测试入口。
- 创建 update card：`/media/yhr/2T/Canon/raw/update-cards/<date>-tasking-<demand-id>-turnover.md`。
- 交付物只作为 URL/artifact refs 记录，不复制到 Canon。

## 更新 state.json

```json
{
  "phase": "dev → test",
  "deliverable_url": "<url1> <url2>",
  "system_test_assignee": "樊亮亮"
}
```

## 完成检查

Turnover 完成跑 gate 脚本——验证需求被干净地移交：

```bash
python3 <skill-dir>/scripts/turnover_gate.py <demand-id> --json
```

输出 `turnover_gate.json`。Turnover 无下游 phase——gate 验证移交状态完整（state/deliverables/comment/assignee/Canon）。
