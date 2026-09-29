---
name: sanitize
description: |
  Close out completed work with scoped commit/push and Canon updates when the user says "收尾", "提交并保存", or "commit and save". Generate a formal evidence-backed task report on "完整任务技术报告", "成果汇报", or "post-task report". Report mode does not commit or push without closeout intent.
---

# Completion Closeout

完成开发后的 scoped publish、Canon closeout，或 formal task report。

Read the shared Canon contract before finalizing meaningful work:

```text
/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md
```

## Mode Routing

- **Closeout** — user asks to commit, push, save, or wrap up completed work.
- **Report** — user asks for a formal end-to-end report on completed work. Read
  `references/formal-report.md`; do not enter git mutation steps.
- **Both** — user explicitly requests report plus closeout. Generate and gate the
  report first, include it in the confirmed file scope, then publish and promote.

A one-incident troubleshooting story belongs to after-action. One reusable
wrong/correct/trigger guardrail belongs to codify.

## Closeout Mode

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

Reuse runtime-native review and Git capabilities:

- Use the shared Review Gate only when equivalent evidence is not already
  recorded by execute, tasking, repair, or traceback.
- Use ordinary scoped Git for local commit/push.
- If the requested outcome includes a GitHub PR, hand off publication to
  `$github:yeet` instead of duplicating PR creation logic here.

## Formal Report Mode

Read `references/formal-report.md` completely, then:

1. Resolve the completed Canon task page.
2. Gather implementation and validation evidence from linked artifacts, commits,
   tests, planning records, and the current repository.
3. Write the 6-section Markdown report to the user-specified or repo-appropriate
   artifact path.
4. Run:

   ```bash
   python3 <skill-dir>/scripts/report_gate.py <report.md>
   ```

5. Record the report's absolute path and durable conclusions in the Canon task
   page or an update card.

If the task is still active, generate an interim report only when explicitly
requested and label missing validation. Report mode alone never commits, pushes,
or marks the task done.


## Workflow Gate Contract

sanitize is the final commit/push/Canon promotion gate and follows the shared workflow output contract:

```text
/home/yhr/.agents/repos/agent-skills/references/skill-output-contract.md
```

Closeout consumes prior implementation, validation, Review Gate, and traceback
evidence. Report mode consumes the same evidence but does not publish code. Neither
mode should create new product behavior while completing the task.

## Gotchas

- Never use `git add .` or commit unrelated dirty work. Scope files from the Canon task page, artifacts, and current diff.
- Do not revert, reset, or overwrite changes you did not make unless the user explicitly asks.
- Do not commit/push when Review Gate is blocked. Fix blockers or record explicit user waiver first.
- A commit without Canon task/update-card progress is incomplete for durable workflows. Record commit hash, review evidence, artifact refs, and next step.
- If no Canon task page can be resolved, stop and ask or create one through the documented task resolution path before claiming wrapup is complete.

## Closeout execution details

For Closeout mode, read [the scoped Git and Canon steps](references/closeout-steps.md) before any mutation.

## 边界情况

- **无改动文件**：提示用户确认是否只做 Canon 收尾。
- **commit message 生成失败**：让用户手动输入。
- **push 失败**：处理冲突后重试，或提示用户手动 push。
- **task page 不存在**：按 `references/canon-task-resolution.md` 创建新 task page。
- **Canon 不可用**：继续 git 收尾，并明确 Canon promotion 未完成。
- **未配置 git user**：提示用户配置 `git config user.name/email`。
