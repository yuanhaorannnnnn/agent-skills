# Briefing — 战情简报与评审安排

## 预检

**第一步：读 gate。在操作知识库或日历之前。**

```bash
cat .proposal/<demand-id>/orient_gate.json
```

| gate verdict | 行为 |
|-------------|------|
| **pass** | 正常进入 Briefing（用户已确认情报摘要，human gate cleared） |
| **ready** | 提示用户"方案已生成，确认情报摘要后回复 OK"——等待用户手动清除 human gate |
| **blocked** | **拒绝启动。** 列出缺失项，提示"回 Orient 补"，停止 |

gate 通过后继续：

1. 确认 CONOPS 方案文档已生成（`state.json` 中 `design_doc_path` 非空）
2. 确认需求关联人员名单已就绪（`state.json` 中 `participants` + `cc`）
3. 确认 `participants` + `cc` 已能解析为 dws calendar 需要的 `userId`；姓名解析不唯一时停止确认，不创建日程

## 执行

### Step 1: 上传方案文档

用 dws 将 `design_doc_path` 指向的方案文档上传到钉钉知识库。
- 目标目录作为参数由用户提供（如 `/Tasking Briefing #1234 --kb-dir /产品方案/OASIS_SIM/`）
- 如果不传 `--kb-dir`，询问目标目录
- 上传成功后获取文档 URL

### Step 2: 更新需求单评论

用 yunxiao MCP 在需求单评论区发布方案文档链接。

### Step 3: 解析评审人员 userId

从 `state.json` 读取 `participants` + `cc`，合并去重为完整名单。

- 如果条目已经是 dws `userId`，直接保留。
- 如果条目是姓名，用 `dws contact user search --query "<name>" --format json` 查询并提取 `userId`。
- 如果某个姓名查不到或返回多个候选，停止并向用户列出该姓名的候选项；不要猜测，也不要创建日程。
- 解析成功后，把 `participant_user_ids` 写入 `state.json`，后续日历命令只使用这些 userId。

### Step 4: 查找空闲时段

优先用 `dws calendar event suggest --users <userId1,userId2> --format json` 查询候选时段；如果当前环境不支持 suggest，再用 `dws calendar busy search --users <userId1,userId2> --format json` 读取原始忙闲数据。

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
- 参与人: Step 3 解析出的 `participant_user_ids`
- 描述: 附上方案文档链接

### Step 6: 更新 state.json

```json
{
  "phase": "plan → review",
  "knowledge_doc_url": "<上传后的文档 URL>",
  "participant_user_ids": ["<userId1>", "<userId2>"],
  "calendar_event_id": "<日历事件 ID>"
}
```

**注意**: 不修改需求单状态，状态保持 `开发_方案评审`。

### Canon promotion

- 更新 Canon task page：记录知识库文档 URL、评审评论、日程 ID、参与人 userId 和当前阶段 `review`。
- 创建 update card：`/media/yhr/2T/Canon/raw/update-cards/<date>-tasking-<demand-id>-briefing.md`。
- 知识库文档和日程只保存 URL/ID 引用，不把文档复制进 Canon。

## 完成检查

Briefing 完成跑 gate 脚本：

```bash
python3 <skill-dir>/scripts/briefing_gate.py <demand-id> --json
```

输出 `briefing_gate.json`。verdict 四态：
- **pass** — machine + human 全过，可以进 Engage
- **ready** — machine 全过，human gate pending（"方案评审待用户确认"）
- **blocked** — machine 有失败，列出缺失项

`ready` 状态时提示用户"方案评审完成后回复 OK，我进 Engage 开发"。
