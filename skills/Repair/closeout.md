# Closeout — 缺陷收尾

## 预检

**第一步：读 gate。在发评论或改状态之前。**

```bash
cat .proposal/repair/<bug-id>/fix_gate.json
```

| gate verdict | 行为 |
|-------------|------|
| **pass** | 正常进入 Closeout |
| **warn** | 进入 Closeout 但告知用户警告项（"review 豁免 / 部分验证不完整"） |
| **blocked** | **拒绝启动。** 列出缺失项，提示"回 Fix 补"，停止 |

gate blocked 时不要"顺便补一下就可以继续"——回 Fix 正式补完后重新跑 gate 生成新的 fix_gate.json。

gate 通过后继续：

1. 读取 `fix_result.json` — **Closeout 主源**。从 `fix_result.verdict/verification/delivery/side_effects/risks` 提取所有需要的数据。
2. 确认 `<bug_root>/state.json` 存在。
2. 确认 `--outcome` 和 `--comment` 已提供。
3. 如果 `--outcome fixed`，确认 Fix 阶段已完成 commit/push，且 `--deliverables` 包含：
   - 代码提交：git commit SHA 或 MR/PR URL（优先使用 Fix 阶段记录的 `commit_sha` / `mr_url`）
   - 构建产物：镜像文件名（Server 端修改）或 whl 文件名（Python API 修改）
   - 已有的 Breach 页（Intake 已发布，不重复贴）
4. 如果 `--outcome fixed`，确认 Fix 阶段已经完成研发自测/构建验证：
   - 长时间构建或打包必须由 `Sentinel` 在 Fix 阶段执行并记录 `sentinel_task_ids`
   - `state.json.self_check_summary` 必须包含 Sentinel 最终状态、关键日志结论，或明确说明未使用 Sentinel 的本地验证命令
   - Closeout 不启动编译、不调用 Sentinel、不执行 git commit/push，只消费 Fix 阶段已经完成的验证和推送结果
5. 不修改负责人；只更新评论区和状态。

## 参数

```text
/Repair Closeout <bug-id> --outcome <type> --comment "..." [...]
```

| outcome | 必填参数 | 默认目标状态 |
|---------|----------|--------------|
| `fixed` | `--comment`, `--deliverables`, `--self-check` | `集成测试中` |
| `false-positive` | `--comment` | `关闭` |
| `requirement` | `--comment` | `转需求` |
| `cannot-reproduce` | `--comment` | `开发挂起` |
| `blocked` | `--comment` | `开发挂起` |

`--deliverables` 格式（`fixed` 时）：
- `<commit_sha>` 或 MR URL
- `http://172.16.19.158:8080/...` 格式的构建产物链接
- Breach 页的 HTTP 链接（`http://172.16.19.158:8080/doc/<bug-id>.html`）

`--self-check` 是研发自测结果摘要，不是测试回归结果。

`Intake` 已经能判断误报、无法复现、转需求时，允许跳过 Fix 直接 Closeout。

## 执行

### Step 1: 上传 self-check 脚本

`fixed` 时，将 self-check 脚本上传为云效附件：

```
mcp__yunxiao__create_workitem_attachment <bug-id> <self_check_script_path>
```

脚本附件的 `fileIdentifier` 记录到 `state.json` 的 `attachment_ids` 中。

### Step 2: 组织评论

所有 outcome 都必须写云效评论。

`fixed` 评论格式：

```
**<bug-id> 修复完成**

分支 <branch>

修复：<一句话修复说明>（<files changed>, +<N>/−<M>）

提交：<commit_sha 或 MR URL>
镜像：<http://172.16.19.158:8080/... 格式的构建产物链接>

自测：<--self-check，包含 Sentinel task id/状态/关键日志结论>。运行时验证需在稳定性环境回测。

自测脚本：已上传至附件。用法：python3 <script_name> --host <host> --port <port> --duration <duration>
```

Breach 链接不重复贴——Intake 已经发过。

其他 outcome 评论格式：

```
结论：<outcome>
说明：<--comment>
```

### Step 3: 更新状态

云效状态字段必须传 status ID，不要传中文状态名。

1. 按 outcome 得到中文目标状态：

   | outcome | 状态 |
   |---------|------|
   | `fixed` | `集成测试中` |
   | `false-positive` | `关闭` |
   | `requirement` | `转需求` |
   | `cannot-reproduce` | `开发挂起` |
   | `blocked` | `开发挂起` |

2. 用 yunxiao MCP `get_work_item_workflow` 查询工作项流程定义，找到目标状态对应的 status ID。
3. 用 `update_work_item` 更新状态：
   - `organizationId`: `5f3f374f6207a1a8b17f933f`
   - `workItemId`: 从 `search_workitems` 结果取
   - `updateWorkItemFields`: `{"status": "<目标状态 status ID>"}`

如果找不到目标状态的 status ID，停止并把 workflow 返回的可用状态列给用户确认；不要尝试传中文名。不修改负责人。

### Step 4: 不修改负责人

Repair 全流程不修改负责人。不要转派给验证者、提单人或其他人。

### Step 5: Canon promotion

- 更新 Canon task page：记录 outcome、目标云效状态、评论证据、deliverable URLs、commit/MR 和下一步。
- `fixed` 的下一步：测试同事在稳定性环境集成测试，通过后改状态为回归验证，再进入 Clear 阶段合入主分支。
- 创建 update card：`/media/yhr/2T/Canon/raw/update-cards/<date>-repair-<bug-id>-closeout.md`。
- Closeout 不复制构建产物，只保存 HTTP 链接和绝对路径 artifact refs。

## 更新 state.json

```json
{
  "phase": "fixed -> integration",
  "outcome": "fixed|false-positive|requirement|cannot-reproduce|blocked",
  "commit_sha": "<git commit>",
  "image_path": "/media/yhr/2T/carla_images/<image_file>",
  "deliverable_urls": ["http://..."],
  "comment_ids": ["<Intake comment ID>", "<Closeout comment ID>"],
  "status": "集成测试中|转需求|关闭|开发挂起",
  "canon_update_card_path": "/media/yhr/2T/Canon/raw/update-cards/<date>-repair-<bug-id>-closeout.md"
}
```

## 完成检查

Closeout 完成跑 gate 脚本验证收尾干净：

```bash
python3 ~/.claude/skills/Repair/scripts/closeout_gate.py <bug-id> --json
```

输出 `closeout_gate.json`。4 项检查：state outcome/status 已填、comment 证据存在、owner 未变（skipped，需 MCP）、Canon 已更新。

Closeout 下游 phase 是 Clear — 测试同事验证通过后，Clear 合入主分支、打包、关闭缺陷。
