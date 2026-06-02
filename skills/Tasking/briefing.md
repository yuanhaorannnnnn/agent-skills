# Briefing — 战情简报与评审安排

## 预检

1. 确认 CONOPS 方案文档已生成（`state.json` 中 `design_doc_path` 非空）
2. 确认需求关联人员名单已就绪（`state.json` 中 `participants` + `cc`）

## 执行

### Step 1: 上传方案文档

用 dws 将 `design_doc_path` 指向的方案文档上传到钉钉知识库。
- 目标目录作为参数由用户提供（如 `/Tasking Briefing #1234 --kb-dir /产品方案/OASIS_SIM/`）
- 如果不传 `--kb-dir`，询问目标目录
- 上传成功后获取文档 URL

### Step 2: 更新需求单评论

用 yunxiao MCP 在需求单评论区发布方案文档链接。

### Step 3: 获取人员名单

从 `state.json` 读取 `participants` + `cc` 合并为完整名单。

### Step 4: 查找空闲时段

对名单中每个人调用 dws calendar busy。

在 **14:00-17:00** 时间窗口内，从今天开始逐日查找：
- 窗口: 14:00-17:00
- 时长: 0.5 小时
- 条件: 名单中**所有人**在该时段均空闲
- 当天无则向后递推一天

边界情况:
- **≥5 天仍未找到**: 停止搜索，上报用户："已搜索 5 个工作日无合适时段，请手动安排评审会议"
- 周末/节假日: dws calendar 会自动跳过

### Step 5: 创建日程

找到空槽后，用 dws calendar event create 创建会议：
- 标题: `[方案评审] <需求标题>`
- 时长: 30 分钟
- 参与人: Step 3 的完整名单
- 描述: 附上方案文档链接

### Step 6: 更新 state.json

```json
{
  "phase": "plan → review",
  "knowledge_doc_url": "<上传后的文档 URL>",
  "calendar_event_id": "<日历事件 ID>"
}
```

**注意**: 不修改需求单状态，状态保持 `开发_方案评审`。

## 完成检查

- [ ] 方案文档已上传知识库
- [ ] 评论区已附文档链接
- [ ] 所有人员空闲时段已查询
- [ ] 评审会议日程已创建（或 5 天无空槽已上报）
- [ ] state.json 已更新
