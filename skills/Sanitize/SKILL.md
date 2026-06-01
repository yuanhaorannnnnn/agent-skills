---
name: Sanitize
description: |
  开发收尾工作流：每次完成一部分开发内容后，自动执行 git 提交/推送、保存 conversation、
  更新 planning 文档。当用户说"开发完成了"、"收尾"、"wrap up"、"完成这部分"、
  "提交并保存"、"done with this"、"commit and save"时触发。
  跨 agent 通用，适配 Claude Code / Codex / Kimi / Pi / Hermes 等不同 runtime 的保存机制。
  Make sure to use this skill whenever the user mentions finishing development, wrapping up,
  committing code, or saving progress after coding work.
---

# Dev Wrapup

完成开发后的一键收尾：提交代码、保存会话、更新进度。

## 触发方式

- "开发完成了"
- "收尾"
- "wrap up"
- "完成这部分"
- "提交并保存"
- "done with this"
- "commit and save"
- "这部分写完了"

## 核心流程

```
1. 检查 git 状态
   └─> 获取改动文件列表
2. 识别当前任务相关文件
   └─> 读取 .planning/conversations/<id>/task_plan.md
   └─> 匹配改动文件与任务范围
3. 生成 commit message
   └─> 基于 diff 摘要 + conventional commits 格式
4. 执行 git commit + push
5. 保存 conversation
   └─> 根据 agent 类型选择正确方式
6. 更新 planning 文档
   └─> 标记已完成项 + 更新 progress.md
```

## 详细步骤

### Step 1: 检查 git 状态

运行 `git status --short` 获取所有改动文件。

### Step 2: 识别当前任务相关文件

读取当前任务的 `task_plan.md`（路径：`.planning/conversations/<conversation-id>/task_plan.md`），提取其中提到的文件路径。与 git status 的输出做匹配：

- 如果 task_plan 中明确列出了文件 → 只提交这些文件
- 如果 task_plan 中没有文件信息 → 提交所有已改动文件
- 如果 task_plan 中提到的文件没有改动 → 提示用户确认

**如何获取 conversation id：**
1. 读取 `.agent-state/ACTIVE_CONVERSATION`
2. 如果不存在，使用当前 git branch 名作为 fallback

### Step 3: 生成 commit message

基于改动的文件和 diff 摘要，生成符合 conventional commits 格式的消息：

```
<type>(<scope>): <description>

[optional body]

Co-Authored-By: Claude <noreply@anthropic.com>
```

**类型判断规则：**
- 主要新增功能 → `feat`
- 修复 bug → `fix`
- 重构代码 → `refactor`
- 更新文档 → `docs`
- 测试相关 → `test`
- 其他 → `chore`

**scope**：取改动最集中的目录名或模块名。

**description**：用一句话概括核心改动（中文或英文，与项目现有 commit 风格一致）。

生成后**向用户展示并确认**，用户可接受、修改或重写。

### Step 4: 执行 git commit + push

用户确认 commit message 后：
1. `git add <相关文件>`
2. `git commit -m "<message>"`
3. `git push`

如果 push 失败（如需要 pull 先），按标准 git 流程处理冲突后重试。

### Step 5: 保存 conversation

根据当前 agent runtime 选择保存方式：

| Runtime | 保存方式 |
|---------|---------|
| Claude Code | 优先尝试 `/save` 命令；如果环境不支持，fallback 到 `save-conversation` skill |
| Codex | 使用 `save-conversation` skill |
| Kimi | 使用 `save-conversation` skill |
| Pi | 使用 `save-conversation` skill |
| Hermes | 使用 `save-conversation` skill |
| 通用 agents | 使用 `save-conversation` skill |

**检测当前 runtime 的方法：**
- 检查 `$HOME/.claude/` 是否存在 → Claude Code
- 检查 `$HOME/.codex/` 是否存在 → Codex
- 检查 `$HOME/.kimi/` 是否存在 → Kimi
- 检查 `$HOME/.pi/` 是否存在 → Pi
- 检查 `$HOME/.hermes/` 是否存在 → Hermes

如果无法检测，默认使用 `save-conversation`。

**如果 save-conversation skill 不可用**，提示用户手动运行保存命令。

### Step 6: 更新 planning 文档

1. 读取 `task_plan.md`，找到当前 phase 下的 checklist items
2. 根据已完成的改动，标记相关 items 为 `[x] 已完成`
3. 在 `progress.md` 中追加一条 session log：
   ```markdown
   ## YYYY-MM-DD HH:MM
   - Completed: [简述完成的内容]
   - Committed: `<commit-hash>`
   - Files changed: [文件列表]
   ```
4. 如果 task_plan 中所有 phases 都已完成，在 task_plan.md 顶部添加 **Status: Complete**

## 输出格式

执行完毕后，向用户汇报：

```markdown
## 收尾完成

- **Git**: 已提交并推送 `<commit-hash>`
- **Conversation**: 已保存 / 已提示手动保存
- **Planning**: 已更新 progress.md，标记 X 项为完成

### 提交详情
- Commit: `<message>`
- Files: [文件列表]
- Branch: `<branch>`
```

## 边界情况

- **无改动文件**：提示用户"当前没有未提交的改动，是否确认收尾？"
- **commit message 生成失败**：让用户手动输入
- **push 失败**：处理冲突后重试，或提示用户手动 push
- **planning 文件不存在**：跳过 planning 更新步骤
- **未配置 git user**：提示用户配置 `git config user.name/email`
