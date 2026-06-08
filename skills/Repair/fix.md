# Fix — 执行修复

## 预检

1. 确认 `<bug_root>/state.json` 中 `phase: intake` 或状态为 `修复中`。
2. 确认 `state.json.fix_plan_path` 指向的 `<repo_root>/.proposal/repair/<bug-id>/fix_plan.md` 存在；若旧 state 缺少该字段，再兼容检查 `<bug_root>/fix_plan.md`。
3. 确认当前分支与 `state.json.fix_branch` 或用户指定分支一致。
4. 检查 worktree：`git diff --quiet && git diff --cached --quiet`，不通过则停止。未跟踪文件（`??`）不计。

## 执行

### Step 1: 读取修复方案

读取：

1. `state.json`
2. `detail.md`
3. `state.json.fix_plan_path` 指向的 `fix_plan.md`
4. 必要附件和日志

### Step 2: 调用 Neutralize

缺陷修复默认使用 Neutralize 的工作流：

1. 提取证据：错误文本、日志、截图、文件路径、行号
2. 尽量复现问题
3. 定位根因
4. 做最小安全修复
5. 跑相关测试或命令验证
6. 搜索邻近文件和相似调用点
7. 编译/自测验证：
   - 需要长时间构建、打包或测试时，调用 `Sentinel`，不要手写 `ghostty -e ...`。
   - Server 端修改示例：
     ```bash
     ~/.agents/repos/agent-skills/skills/Sentinel/scripts/sentinel.sh run \
       --id <bug-id>-package \
       --title "<bug-id> Package Build" \
       --cwd <repo-path> \
       --conda-env py38 \
       --env PYTHON_EXECUTABLE=$(which python) \
       --lines 80 \
       -- ./package.sh
     ```
   - Python API 修改示例：
     ```bash
     ~/.agents/repos/agent-skills/skills/Sentinel/scripts/sentinel.sh run \
       --id <bug-id>-python-api \
       --title "<bug-id> Python API Build" \
       --cwd <repo-path> \
       --lines 80 \
       -- cmake --build Build --target carla-python-api -j 24
     ```
   - `run` 会在 agent 侧阻塞到最终状态，只返回最终摘要、最后日志和错误摘要；失败时 Fix 未完成。
   - 编译失败则视为 fix 未完成，不能进入 Closeout。
8. 总结修复、相似问题、剩余风险

### Step 3: Review Gate

验证通过后、提交并推送前，读取共享质量门：

```text
/home/yhr/.agents/repos/agent-skills/references/review-gate.md
```

用本缺陷的 Canon task page、`fix_plan.md`、当前 diff、Sentinel 或本地验证摘要做 review。优先使用跨 runtime reviewer；不可用时执行本地 adversarial review 并说明。

- 有 blocker：停在 Fix，修复后重新验证和 review，不 commit、不 push、不进入 Closeout。
- 无 blocker：把 review 结果写入 Canon task page § Findings / § Evidence / § Timeline，并继续提交推送。

### Step 4: 提交并推送

Review Gate 通过后提交并推送修复分支，失败则停在 Fix，不进入 Closeout。

前置条件：
- 当前分支等于 `state.json.fix_branch` 或用户明确指定的修复分支
- Sentinel/本地验证已通过，`self_check_summary` 已准备好
- Review Gate 已通过，或用户明确豁免 blocker
- `git status --short` 中只包含本缺陷相关改动；如有无关改动，停止并让用户处理

执行：
1. 查看 `git status --short` 和 `git diff --stat`，确认提交范围
2. `git add <本缺陷相关文件>`，不要 `git add .` 混入无关文件
3. `git commit -m "fix: <bug-id> <summary>"`
4. `git push -u origin <fix_branch>`
5. 记录 `commit_sha`、`pushed_branch`、`remote_url`；如果能获得 MR/PR URL，也记录 `mr_url`

获取 MR/PR URL 的优先级：
- 如果 push 输出包含平台创建 MR/PR 的 URL，直接记录。
- 如果项目使用 `gh` / `glab` / Codeup CLI 且已配置认证，查询当前分支对应的 open MR/PR。
- 如果无法获得 MR/PR URL，记录 remote branch URL 和 commit SHA，并在 Closeout 评论里说明暂无 MR/PR 链接。

### Step 5: 条件触发 Codify

只有符合以下任一条件时触发 Codify：

- 同一错误模式在多处出现
- 修复暴露了误读需求或流程级防错规则
- 用户要求“记下来”或“写成规则”
- 规则适合沉淀为 Canon `patterns/` 或 `incidents/`，必要时兼容写入 repo-local `.agent-state/rules/mistakes.md`

### Step 6: 条件触发 AfterAction

只有符合以下任一条件时触发 AfterAction：

- 修复过程复杂或耗时较长
- 走过明显弯路，后续 agent 可能再次踩坑
- 用户要求复盘、修复记录、debug 总结
- 结论值得沉淀给 6 个月后的自己

## Canon promotion

- 更新 Canon task page：记录修复摘要、验证摘要、review 结果、Sentinel task id、commit/MR、构建产物和剩余风险。
- 创建 update card：`/media/yhr/2T/Canon/raw/update-cards/<date>-repair-<bug-id>-fix.md`。
- Codify/AfterAction 的长期结论优先沉淀到 Canon `patterns/` 或 `incidents/`；repo-local 规则文件只作为项目内运行时兼容入口。

## 更新 state.json

```json
{
  "phase": "intake -> fixing -> fixed",
  "fix_summary": "...",
  "self_check_summary": "...",
  "sentinel_task_ids": ["<bug-id>-package"],
  "build_artifacts": ["/media/yhr/2T/carla_images/<artifact>"],
  "commit_sha": "<git commit>",
  "pushed_branch": "<fix_branch>",
  "remote_url": "<origin branch URL>",
  "mr_url": "<MR/PR URL if available>",
  "review_summary": "...",
  "review_gate": "passed|blocked|skipped",
  "similar_issues_checked": ["..."],
  "codify_rule_path": "...",
  "after_action_path": "..."
}
```

`self_check_summary` 是研发自测摘要，不是测试回归结果；如果使用 Sentinel，摘要必须包含 Sentinel task id、最终状态和关键日志结论。

## 完成检查

- [ ] 根因已定位
- [ ] 最小修复已完成
- [ ] 相关验证已运行，或未运行原因已写明
- [ ] Server 端修改 → Sentinel 监控的 `./package.sh` 编译通过，或 Python API 修改 → Sentinel/本地 `cmake --build` 通过
- [ ] Sentinel task id 和构建产物已写入 `state.json`
- [ ] 修复分支已 commit 并 push，commit_sha/pushed_branch 已写入 `state.json`
- [ ] Review Gate 已通过，或 blocker 已修复/用户明确豁免
- [ ] 相似问题已检查
- [ ] 必要时已触发 Codify
- [ ] 必要时已触发 AfterAction
- [ ] 未修改负责人
- [ ] `state.json` 已更新
- [ ] Canon task/update-card 已记录 Fix 证据或明确记录未完成原因
