# Closeout execution steps

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

如果当前 diff 已在 `repair Fix`、`tasking Engage` 或 `execute` 中通过等价 Review Gate，可记录证据后跳过重复 review。否则用 Canon task page、当前 diff、验证摘要执行 review。

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

如果当前工作没有对应的 Canon task page，按 `canon-task-resolution.md` 的 resolution 逻辑创建。

## Step 6: 更新 task page § Tasks

如果 task page 有 § Tasks checklist，将本次完成的项标记为 `[x]`。

如果 task_plan 所有 phases 完成，更新 task page frontmatter `status: done`。

旧版 `.planning/conversations/` 下的 progress.md 不再更新——task page 是唯一的进度记录点。

## Step 7: Gate

收尾完成跑 gate——验证 commit、push、Canon 更新都落地了：

```bash
python3 <skill-dir>/scripts/wrapup_gate.py --task <canon-task-path> --repo <path>
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
