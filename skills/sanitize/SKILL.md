---
name: Sanitize
description: |
  开发收尾工作流：每次完成一部分开发内容后，执行 git 提交/推送、更新 Canon
  task page、并把长期项目/任务/决策/artifact 信息提升到 Canon。
  当用户说"开发完成了"、"收尾"、"wrap up"、"完成这部分"、"提交并保存"、
  "done with this"、"commit and save"时触发。跨 agent 通用，适配 Claude Code /
  Codex / Kimi / Pi 等不同 runtime。
---

# Dev Wrapup

完成开发后的一键收尾：提交代码、更新 Canon task page、把 durable context 推进 Canon。

Read the shared Canon contract before finalizing meaningful work:

```text
/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md
```

## 核心流程

```text
1. 检查 git 状态
2. 识别当前任务相关文件
3. 生成并确认 commit message
4. 执行 Review Gate（如本 diff 尚未通过）
5. 执行 git commit + push
6. 更新 Canon task page（替代旧的 runtime conversation 保存）
7. 更新 Canon task page § Progress / § Evidence / § Timeline
8. 写入 Canon update card / artifact reference
```


## Workflow Gate Contract

Sanitize is the final commit/push/Canon promotion gate and follows the shared workflow output contract:

```text
/home/yhr/.agents/repos/agent-skills/references/skill-output-contract.md
```

It consumes prior implementation, validation, Review Gate, and Traceback evidence. It should not create new product behavior while trying to close the task.

## Gotchas

- Never use `git add .` or commit unrelated dirty work. Scope files from the Canon task page, artifacts, and current diff.
- Do not revert, reset, or overwrite changes you did not make unless the user explicitly asks.
- Do not commit/push when Review Gate is blocked. Fix blockers or record explicit user waiver first.
- A commit without Canon task/update-card progress is incomplete for durable workflows. Record commit hash, review evidence, artifact refs, and next step.
- If no Canon task page can be resolved, stop and ask or create one through the documented task resolution path before claiming wrapup is complete.

## Step 1: 检查 git 状态

运行 `git status --short` 获取所有改动文件。

## Step 2: 识别当前任务相关文件

从 Canon task page 获取关联文件范围：

```text
/media/yhr/2T/Canon/tasks/<task-id>.md
```

匹配规则：

1. task page 的 § Artifacts 或 § Plan 明确列出文件 → 优先提交这些文件
2. 通过 project + branch 反推 task page（task page resolution logic）
3. 没有 task page → 提交所有已改动文件前向用户确认
4. 出现无关改动 → 停止并让用户确认范围

不再依赖 `ACTIVE_CONVERSATION` 或 `.planning/conversations/` 来确定任务身份——Canon task page 是唯一来源。

## Step 3: 生成 commit message

基于改动文件和 diff 摘要生成 conventional commits 格式。生成后向用户展示并确认。

## Step 4: 执行 git commit + push

提交前读取共享质量门：

```text
/home/yhr/.agents/repos/agent-skills/references/review-gate.md
```

如果当前 diff 已在 `Repair Fix`、`Tasking Engage` 或 `Execute` 中通过等价 Review Gate，可记录证据后跳过重复 review。否则用 Canon task page、当前 diff、验证摘要执行 review。

- 有 blocker：停止，不 commit、不 push。
- 无 blocker：把 review 结果写入 task page § Findings / § Evidence / § Timeline，然后继续提交。

用户确认后：

1. `git add <相关文件>`，不要无脑 `git add .`
2. `git commit -m "<message>"`
3. `git push`

如果 push 失败，按标准 git 流程处理冲突后重试，或提示用户手动处理。

## Step 5: 更新 Canon task page

更新对应的 Canon task page 的 § Progress、§ Artifacts、§ Evidence 和 § Timeline：

```text
/media/yhr/2T/Canon/tasks/<task-id>.md
```

追加到 § Progress：

```markdown
### YYYY-MM-DD HH:MM
- Completed: <简述完成内容>
- Committed: `<commit-hash>`
- Files changed: <文件列表>
```

更新 § Artifacts 中变更的文件引用。

如果本次执行了 Review Gate，§ Evidence 记录 reviewer/命令/证据路径，§ Timeline 记录 `review_passed` 或 `review_blocked`。

如果当前工作没有对应的 Canon task page，按 `references/canon-task-resolution.md` 的 resolution 逻辑创建。

## Step 6: 更新 task page § Tasks

如果 task page 有 § Tasks checklist，将本次完成的项标记为 `[x]`。

如果 task_plan 所有 phases 完成，更新 task page frontmatter `status: done`。

旧版 `.planning/conversations/` 下的 progress.md 不再更新——task page 是唯一的进度记录点。

## Step 7: Gate

收尾完成跑 gate——验证 commit、push、Canon 更新都落地了：

```bash
python3 ~/.claude/skills/Sanitize/scripts/wrapup_gate.py --task <canon-task-path> --repo <path>
```
blocked → commit 缺失 / 未 push / Canon 未更新。pass → 收尾完成。

## Step 8: Canon promotion

对有长期价值的收尾，创建或更新：

```text
/media/yhr/2T/Canon/raw/update-cards/YYYYMMDD-<task-or-branch>-wrapup.md
```

Update card 至少记录：

- project
- task
- commit hash / branch / remote URL
- changed files
- decisions or incidents supported
- artifacts produced, using absolute paths
- next step

如果交付物是 build/report/proposal/log，不复制到 Canon；写入 `artifacts/artifact-index.md` 或 update card 的 absolute path。

## 输出格式

```markdown
## 收尾完成

- **Git**: 已提交并推送 `<commit-hash>`
- **Canon Task Page**: 已更新 /media/yhr/2T/Canon/tasks/<task>.md
- **Canon**: 已写 update card / 无 durable 更新 / Canon 不可用

### 提交详情
- Commit: `<message>`
- Files: <文件列表>
- Branch: `<branch>`
- **Evidence/Timeline**: 如有新增 Canon decision/incident 或阶段变更，追加到 task page § Evidence / § Timeline（optional）
```

## 边界情况

- **无改动文件**：提示用户确认是否只做 Canon 收尾。
- **commit message 生成失败**：让用户手动输入。
- **push 失败**：处理冲突后重试，或提示用户手动 push。
- **task page 不存在**：按 `references/canon-task-resolution.md` 创建新 task page。
- **Canon 不可用**：继续 git 收尾，并明确 Canon promotion 未完成。
- **未配置 git user**：提示用户配置 `git config user.name/email`。
