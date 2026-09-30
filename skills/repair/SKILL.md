---
name: repair
description: |
  处理已由 Phase 0 拉取的云效缺陷单，按 Intake、Fix、Closeout、Clear 四阶段推进。触发于"处理缺陷"、"修复缺陷单"、"云效缺陷"、缺陷 ID 加"处理/修复/提测"，或 /repair 各 mode；不用于普通调试（用 neutralize）。不改变缺陷负责人。
---

# repair — 云效缺陷修复流程

一个 skill，四个 mode。缺陷单原始上下文由共享 Phase 0 生成，repair 只负责接单分析、修复和收尾。

## 路由

| Mode | 触发 | 文件 |
|------|------|------|
| `Intake` | `/repair Intake <bug-id> --base <branch>` | `intake.md` |
| `Fix` | `/repair Fix <bug-id>` | `fix.md` |
| `Closeout` | `/repair Closeout <bug-id> --outcome <type> --comment "..." ...` | `closeout.md` |
| `Clear` | `/repair Clear <bug-id>` | `clear.md` |

参数不匹配任何 mode 时，列出上表用法。匹配后立即读取对应 mode 文件执行完整流程。

## 全局约定

- **缺陷目录**: `/media/yhr/2T/yunxiao/bugs/<bug-id>/` — Phase 0 原始材料和
  `state.json` 的存放位置。`detail.md`、附件和其他 raw 输入只读；`state.json`
  仅允许按下方 mode 字段表 scoped write
- **产物目录**: `<artifact-dir>/` — 所有 Intake 生成的产物（`root-cause.md`、`fix_plan.json`、breach HTML）写入当前 repo 的此路径
- **Phase 0**: 与需求开发共用同一个 yunxiao 定时任务；只抓取、下载、创建本地文件、发通知，不改云效状态
- **输入状态**: Phase 0 当前样本已生成 `state.json`、`detail.md`，图片/日志附件可平铺在缺陷目录
- **状态集合**: `待处理`、`重新打开`、`修复中`、`开发挂起`、`集成测试中`、`回归验证`、`转需求`、`关闭`
- **负责人规则**: 全流程不修改负责人；只读负责人字段，只修改评论区和缺陷状态
- **分支规则**: `--base <branch>` 从 base 创建 `bugfix/<bug-id>`；dirty worktree 停止，不自动 stash
- **breach 页面**: 每次 Intake 必生成 `<artifact-dir>/index.html`
- **缺字段策略**: 先用现有 `state.json`；Intake 能从云效实时补查就写回，补不到关键字段再问用户


## Workflow Gate Contract

repair modes must satisfy the shared workflow output contract:

```text
/home/yhr/.agents/repos/agent-skills/references/skill-output-contract.md
```

Each mode must leave a resumable handoff: `state.json`, Canon task page, update card, and mode-specific artifacts (`root-cause.md` + `fix_plan.json`, breach page, `fix_gate.json`, monitor state, commit/MR, or Closeout comment).

## Resources

- `intake.md` — Intake phase execution instructions
- `fix.md` — Fix phase execution instructions
- `closeout.md` — Closeout phase execution instructions
- `clear.md` — Clear phase execution instructions
- `references/fix_plan_schema.md` — fix_plan.json schema + gate behavior
- `references/fix_result_schema.md` — fix_result.json schema + gate behavior
- `scripts/intake_gate.py` — Intake gate checker
- `scripts/fix_gate.py` — Fix gate checker
- `scripts/closeout_gate.py` — Closeout gate checker
- Runtime artifacts: `fix_gate.json`, `closeout_gate.json` (each phase's entry defense)

## Gotchas

- Yunxiao status updates require status IDs from `get_work_item_workflow`; do not pass Chinese display names such as `修复中` or `回归验证` to update APIs.
- repair never changes the defect assignee/owner. Only comments and defect status are mutable unless the user explicitly changes this rule.
- `Fix` may run monitored builds/tests; `Closeout` must not start a new build. Closeout consumes `self_check_summary`, deliverable links, and Review Gate evidence from Fix.
- Every outcome needs a Yunxiao comment. Fixed, false positive, transferred-to-demand, and closed all need explicit evidence or clarification text.
- Do not enter Closeout until Review Gate blockers are fixed or explicitly waived.
- `Clear` is the only phase that merges to the base branch and starts a new package build. It must only run after the tester confirms regression verification.

## Canon 输出边界

读取共享契约：`/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md`。

- `<bug_root>/state.json` 是 Phase 0/repair 阶段门控文件，`<artifact-dir>/` 是修复方案 artifact 目录。
- 缺陷长期状态写入 Canon task page：`/media/yhr/2T/Canon/tasks/<bug-id>.md`，记录根因、修复分支、验证证据、交付物、云效状态和下一步。
- `root-cause.md`、breach HTML、validation task、commit/MR、镜像 HTTP 链接、after-action/codify 产物都作为 Canon artifact refs。
- 每个 mode 完成后创建或更新 `/media/yhr/2T/Canon/raw/update-cards/<date>-repair-<bug-id>-<mode>.md`。
- repair 全流程不修改负责人；Canon 也只记录 owner/validator 信息，不把它当作状态修改动作。

## State 更新边界

| Mode | 可写字段 |
|------|----------|
| `Intake` | `phase`, `status`, `base_branch`, `fix_branch`, `repo_path`, `severity`, `priority`, `attachment_paths`, `agent_prompt_path`, `diagnosis_summary`, `root_cause_path`, `proposal_page_path`, `share_url`, `canon_task_path`, `canon_update_card_path` |
| `Fix` | `phase`, `fix_summary`, `self_check_summary`, `validation_task_ids`, `build_artifacts`, `review_summary`, `review_gate`, `commit_sha`, `pushed_branch`, `remote_url`, `mr_url`, `similar_issues_checked`, `codify_rule_path`, `after_action_path`, `canon_update_card_path`, `canon_artifact_refs` |
| `Closeout` | `phase`, `outcome`, `deliverable_urls`, `comment_ids`, `status`, `canon_update_card_path`, `canon_artifact_refs` |
| `Clear` | `phase`, `status`, `merge_commit_sha`, `clear_build_artifact`, `deliverable_urls`, `comment_ids`, `canon_update_card_path`, `canon_artifact_refs` |

不要覆盖自己负责范围外的字段。

## 项目材料路径优先

先读取目标项目文档规则。CARLA 同时具有 `.agent-artifacts-repo-owned` 与 `Docs/guides/documentation.md` 时，artifact-dir 为 `Docs/tasks/repair-<bug-id>/`，runtime-dir 为 `.local/tasks/同一任务slug/`；其他项目 artifact-dir 保留 `.proposal/repair/<bug-id>/`，runtime-dir 保留 `.planning/<id>/`。下列阶段文件中的 artifact-dir/runtime-dir 均使用此解析结果，不能直接照抄旧路径示例。阶段 gate 使用相同解析器。创建 gate JSON 或衍生附件后按项目归属规则登记 sidecar，再检查、提交；执行缓存留本地。
