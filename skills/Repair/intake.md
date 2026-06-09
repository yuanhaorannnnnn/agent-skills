# Intake — 接单分析与修复方案

## 预检

1. 确认当前在目标代码仓库，或 `state.json.repo_path` 指向目标仓库。
2. 确认 `/media/yhr/2T/yunxiao/bugs/<bug-id>/state.json` 和 `detail.md` 存在。
3. 检查 worktree：`git diff --quiet && git diff --cached --quiet`，不通过则停止并提示用户处理未提交修改（不自动 stash）。未跟踪文件（`??`）不计为 dirty。
4. 确认参数包含 `<bug-id>`，并且 `--branch` / `--base` 二选一。

## 参数

必须显式指定分支参数，不允许无参自动创建。

| 参数 | 必填 | 行为 |
|------|------|------|
| `<bug-id>` | 是 | 定位缺陷目录和云效缺陷单 |
| `--base` (无值) | 二选一 | 从当前分支创建 `bugfix/<bug-id>` |
| `--base <branch>` | 二选一 | 从指定 base 创建 `bugfix/<bug-id>` |
| `--branch` (无值) | 二选一 | 使用当前分支，不切换不创建 |
| `--branch <name>` | 二选一 | 切换到指定已有分支，不创建 |

不传任何分支参数 → 报错，提示用户必须指定 `--base` 或 `--branch`。

## 执行

### Step 1: 加载缺陷上下文

按顺序读取：

1. `state.json` — 标题、状态、负责人、创建人、本地目录、需求关联等 Phase 0 快照
2. `detail.md` — 缺陷正文、复现路径、评论历史
3. `<bug_root>/*.{png,jpg,jpeg,mp4,log,txt}` — 截图、视频、日志等附件

如果 `severity`、`priority`、`repo_path` 等修复字段缺失，尝试从云效实时补查并写回 `state.json`。补不到关键字段时停止向用户确认。

### Step 2: 切换分支

- `--branch` (无值): 使用当前分支，不切换。
- `--branch <name>`: 非破坏性切换到已有分支。
- `--base` (无值): 从当前分支创建 `bugfix/<bug-id>`。
- `--base <branch>`: 切换到 base 后创建 `bugfix/<bug-id>`。
- 不自动 stash，不覆盖用户未提交修改。

### Step 3: 结合代码分析

以缺陷标题、复现步骤、错误日志、截图文字、关联需求为线索定位代码：

- 先用 `rg` 搜索错误文本、模块名、接口名、场景名、传感器名等关键词
- 必要时用 Overwatch 拉远看模块位置
- 如果错误来自 CARLA C++ 端（`RuntimeError: std::exception`），先翻日志找到调用链末端的 Python 函数名，再用 `rg` 反向搜索 C++ 侧对应的实现
- 输出根因假设、受影响文件、最小修复点、验证命令
- 不确定点列出给用户，不要自行假设

### Step 4: 生成修复方案

写入两份文件：

**1. `fix_plan.md`**（人读）— `<repo_root>/.proposal/repair/<bug-id>/fix_plan.md`。

```markdown
# <bug-id> 修复方案

## 缺陷摘要
[一句话说明问题]

## 复现路径
[操作步骤、URL、输入数据、环境]

## 定位结论
- `path/to/file`: [疑似原因]

## 修复方案
- 根因假设: ...
- 最小修复点: ...
- 验证命令: ...

## 待确认
- ...
```

**2. `fix_plan.json`**（Machine 读）— 按 `references/fix_plan_schema.md` 的 schema 生成。Fix Agent 以此为主源。`root_cause.confidence` 为 `speculative` 的项 + `uncertainties` 中 `impact: blocking` 的项会在 gate 检查时导致 blocked。

### Step 5: 生成 Breach 对齐页

调用 Breach 生成 `.proposal/repair/<bug-id>/index.html`。页面类型按 `12-incident-report.html` 的单页报告结构组织：

- 缺陷摘要
- 影响范围
- 复现/时间线
- 根因假设
- 修复方案
- 验证计划
- 风险和后续

Breach 页面是快速对齐材料，不替代 `fix_plan.md`。

**双重落盘**：生成后复制到 LAN 分享目录：

```bash
cp <repo_root>/.proposal/repair/<bug-id>/index.html /media/yhr/2T/carla_images/doc/<bug-id>.html
```

### Step 6: 评论区 + 云效状态

**评论区**格式（只写分行 + HTTP 链接，不贴文件路径）：

```
**<bug-id> 修复中**

分支 <branch> | 根因：<一句话>

修复方案：http://172.16.19.158:8080/doc/<bug-id>.html
```

**状态更新**：云效状态字段必须传 status ID，不要传中文状态名。

1. 先用 yunxiao MCP `get_work_item_workflow` 查询当前工作项的流程定义，找到中文状态 `修复中` 对应的 status ID。
2. 再用 `update_work_item` 更新状态：
   - `organizationId`: `5f3f374f6207a1a8b17f933f`
   - `workItemId`: 从 `search_workitems` 结果中取
   - `updateWorkItemFields`: `{"status": "<修复中 status ID>"}`

如果找不到 `修复中` 的 status ID，停止并把 workflow 返回的可用状态列给用户确认；不要尝试传中文名。

不修改负责人。

## Canon promotion

- 创建或更新 Canon task page：`/media/yhr/2T/Canon/tasks/<bug-id>.md`，记录缺陷摘要、当前状态 `修复中`、修复分支、根因假设、风险和下一步 `Fix`。
- 创建 update card：`/media/yhr/2T/Canon/raw/update-cards/<date>-repair-<bug-id>-intake.md`。
- 把 `fix_plan.md`、Breach HTML、LAN 分享 URL、缺陷目录作为 artifact refs；不要把 Phase 0 原始材料复制进 Canon。

## 更新 state.json

```json
{
  "phase": "new -> intake",
  "status": "修复中",
  "base_branch": "<branch>",
  "fix_branch": "<branch-or-bugfix>",
  "fix_plan_path": "<repo_root>/.proposal/repair/<bug-id>/fix_plan.md",
  "proposal_page_path": "<repo_root>/.proposal/repair/<bug-id>/index.html",
  "share_url": "http://172.16.19.158:8080/doc/<bug-id>.html",
  "canon_task_path": "/media/yhr/2T/Canon/tasks/<bug-id>.md",
  "canon_update_card_path": "/media/yhr/2T/Canon/raw/update-cards/<date>-repair-<bug-id>-intake.md"
}
```

所有路径用绝对路径，以 `git rev-parse --show-toplevel` 得到的仓库根目录为基准。

## 完成检查

Intake 完成必须跑 gate 脚本——不再靠 Agent 自己打勾：

```bash
python3 ~/.claude/skills/Repair/scripts/intake_gate.py <bug-id> --json
```

输出 `fix_gate.json`，verdict 三态：
- **pass** — 可以进 Fix
- **blocked** — 不可进 Fix，列出缺失项
- **warn** — 可以进 Fix 但某几项有警告（`root_cause.confidence: speculative` / `uncertainties` 有 `clarifying`）

gate 脚本会检查 9 项中的 7 项（yunxiao 状态和负责人检查需要 MCP auth，本地跳过）。

## Handoff to Fix

Intake 写入 `fix_plan.json`（按 `references/fix_plan_schema.md` 的 schema），Fix Agent 的独立判定由此 JSON 做出。gate 脚本检查 `fix_plan.json` 的 `root_cause.hypothesis` 和 `fix_plan.modified_files` 非空——不通过则 blocked。

`fix_gate.json` 是 Fix 的入口防线。Fix Agent 启动第一步读 gate → blocked 则拒绝 → warn 则继续但告知用户风险。
