# Clear — 合入主分支

## 预检

**第一步：读 closeout gate。在碰任何代码之前。**

```bash
cat .proposal/repair/<bug-id>/closeout_gate.json
```

| gate verdict | 行为 |
|-------------|------|
| **pass** | 正常进入 Clear |
| **blocked** | **拒绝启动。** 回 Closeout 补 |

gate 通过后继续：

1. 确认 `<bug_root>/state.json` phase 为 `integration`。
2. 确认 `base_branch` 非空。
3. 确认 Fix 阶段已完成 commit/push，`commit_sha` / `pushed_branch` 非空。

## 执行

### Step 1: 轮询云效状态

用 yunxiao MCP `get_work_item` 查询缺陷状态。如果状态为 `集成测试中`，提示用户等待测试完成并停止。如果状态为 `回归验证`，进入 Step 2。

```text
状态 = 集成测试中  → 停止。"等待测试同事在稳定性环境完成集成测试，状态变为 回归验证 后重新执行 Clear。"
状态 = 回归验证    → 继续 Step 2
其他状态           → 停止。提示用户确认当前状态。
```

### Step 2: 合入主分支

```bash
git checkout <base_branch>     # 从 state.json.base_branch 读取
git pull
git merge bugfix/<bug-id>      # 从 state.json.fix_branch 读取
git push origin <base_branch>
```

冲突时停止，提示用户手动 resolve 后继续。

### Step 3: 打包

使用 monitored execution 运行 `package_fast.sh`，记录构建产物 tag 到 state.json。

### Step 4: 验证

重跑 `self_check` 脚本（存在则跑）。合入后的构建必须通过相同的自测。

### Step 5: 云效收尾

**评论**：

```
**<bug-id> 已合入并关闭**

合入：<base_branch> (commit <sha>)
构建：<http://172.16.19.158:8080/...tar>
自测：<self-check result>
```

**状态更新**：`update_work_item` status → `关闭` (status ID: `1a58efef8b59745fdb83215f36`)。

## Canon promotion

- 更新 Canon task page：记录合入分支、构建产物、最终状态 关闭。
- 创建 update card：`/media/yhr/2T/Canon/raw/update-cards/<date>-repair-<bug-id>-clear.md`。

## 更新 state.json

```json
{
  "phase": "integration -> done",
  "status": "关闭",
  "merge_commit_sha": "<merge commit>",
  "clear_build_artifact": "carlaue5:202606XXXXXX",
  "deliverable_urls": ["http://..."],
  "comment_ids": ["<Intake>", "<Closeout>", "<Clear>"],
  "canon_update_card_path": "/media/yhr/2T/Canon/raw/update-cards/<date>-repair-<bug-id>-clear.md"
}
```

## 完成检查

Clear 完成跑 gate 脚本：

```bash
python3 <skill-dir>/scripts/clear_gate.py <bug-id> --json
```

输出 `clear_gate.json`。检查：merge 完成、commit 存在、构建产物存在、云效状态为关闭、Canon 已更新。

Clear 是 Repair 最后一个阶段——缺陷已合入主分支并关闭。
