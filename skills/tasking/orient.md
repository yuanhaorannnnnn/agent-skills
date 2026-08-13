# Orient — 情报分析与方案生成

## 预检

1. 确认当前在项目代码仓库根目录下
2. 检查 worktree：`git diff --quiet && git diff --cached --quiet`，不通过则停止并提示用户处理未提交修改（不自动 stash）。未跟踪文件（`??`）不计为 dirty。
3. 确认 `/media/yhr/2T/yunxiao/requirements/<demand-id>/` 存在且包含 `state.json` 和 `detail.md`

## 分支管理

必须显式指定分支参数，不允许无参自动创建。

| 参数 | 行为 |
|------|------|
| `--base` (无值) | 从当前分支创建 `feature/<demand-id>` |
| `--base <branch>` | 切到指定 base 分支后创建 `feature/<demand-id>` |
| `--branch` (无值) | 使用当前分支，不切换不创建 |
| `--branch <name>` | 切换到指定已有分支，不创建 |

不传任何分支参数 → 报错，提示用户必须指定 `--base` 或 `--branch`。

从 `state.json` 读取需求标题作 commit 上下文。

## 情报收集

### Step 1: 加载需求文档

按顺序读取：
1. `state.json` — 获取结构化元数据（参与人、抄送人、项目、状态）
2. `detail.md` — 需求描述和全部评论历史
3. `prd.md` — PRD 文档（如有）
4. `builtin_params.csv` — 内置参数表（如有）
5. `ux_doc_paths` 指向的 UI/UX 文件（如有）

### Step 2: 分析代码库

以需求描述中的关键词为线索，在当前分支代码库中定位受影响的模块：
- 扫描目录结构、入口点和调用关系，建立代码库整体视图
- 定位需要修改的具体文件和函数
- 识别接口边界和依赖关系

### Step 3: 输出情报摘要

用 Markdown 输出分析结果：

```markdown
## 需求摘要
[一段话概括需求目标]

## 受影响模块
- `path/to/module1`: [改动内容]
- `path/to/module2`: [改动内容]

## 接口影响
[API/配置文件/SDK 方法变更点]

## 待确认
- [不确定的点 1]
- [不确定的点 2]
```

**关键原则**: 不确定的点必须列出来等你确认，不要自行假设后直接推进。

## 方案生成

用户确认情报摘要后，调用 CONOPS 生成技术方案：

1. 将情报摘要 + state.json 中的需求元数据传递给 CONOPS
2. CONOPS 输出到 `.proposal/<demand-id>/<demand-id>-design.md`
3. 更新 `state.json`:
   - `phase`: `new` → `plan`
   - `design_doc_path`: 方案文件绝对路径（例如 `.proposal/dingtalk-codeup-workflow/<demand-id>-design.md`）
   - `participants` / `cc`: 从需求单读取（如果 Phase 0 未写入）

### Canon promotion

- **方案 artifact**: `.proposal/<demand-id>/<demand-id>-design.md` — repo-local 方案文档
- 创建或更新 Canon task page：`/media/yhr/2T/Canon/tasks/<demand-id>.md`，记录需求摘要、base/feature branch、方案 artifact、待确认问题和下一阶段 `Briefing`。
- 创建 update card：`/media/yhr/2T/Canon/raw/update-cards/<date>-tasking-<demand-id>-orient.md`，链接 `design_doc_path`、需求目录和代码分析证据。

## 完成检查

Orient 完成跑 gate 脚本：

```bash
python3 <skill-dir>/scripts/orient_gate.py <demand-id> --json
```

输出 `orient_gate.json`。verdict 四态：
- **pass** — machine + human 全过，可以进 Briefing
- **ready** — machine 全过，human gate pending（"情报摘要待用户确认"）
- **blocked** — machine 有失败，列出缺失项
- **warn** — machine 全过但有轻微问题

`ready` 状态时提示用户"情报摘要已生成，请确认后说 OK"。不自动进 Briefing。
