# Turnover — 任务移交

## 预检

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

用 yunxiao MCP 将需求单状态改为 `系统测试`。

## 更新 state.json

```json
{
  "phase": "dev → test",
  "deliverable_url": "<url1> <url2>"
}
```

## 完成检查

- [ ] 评论区已附交付物链接清单
- [ ] 需求单状态已改为 `系统测试`
- [ ] state.json 已更新
