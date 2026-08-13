# Fix — 执行修复

## 预检

**第一步：读 gate。在碰任何代码之前。**

```bash
cat .proposal/repair/<bug-id>/intake_gate.json
```

| gate verdict | 行为 |
|-------------|------|
| **pass** | 正常进入 Fix |
| **warn** | 进入 Fix 但把警告内容告知用户（"root_cause.confidence 为 speculative，修复可能不准"） |
| **blocked** | **拒绝启动。** 列出缺失项，提示"回 Intake 补"，停止 |

gate blocked 时不要"顺便补一下就可以继续"——回 Intake 正式补完后重新跑 gate 生成新的 intake_gate.json。

gate 通过后继续以下预检：

1. 确认 `<bug_root>/state.json` 中 `phase` 为 `intake`。
2. 确认 `fix_plan.json` 存在——Fix 以此为主源，`root-cause.md` 为人工阅读补充。
3. 确认当前分支与 `state.json.fix_branch` 一致。
4. 检查 worktree：`git diff --quiet && git diff --cached --quiet`，不通过则停止。

## 执行

### Step 1: 读取修复方案

按顺序读取：

1. `fix_plan.json` — **主源**。含 root_cause/confidence/files/modified_files/uncertainties/related_code/attachments。修复决策基于此 JSON 做出。
2. `root-cause.md` — 根因分析报告（人读，Intake 产物）。
3. `state.json` + `detail.md` + 附件（按 `fix_plan.json.attachments` 列表读取）

### Step 2: 生成目标文件

基于 `root-cause.md` 的深度分析，生成 `goal.md` — 广度行动计划。

写入 `<repo_root>/.proposal/repair/<bug-id>/goal.md`：

```markdown
# <bug-id> 修复目标

## 目标
[一句话：修复什么]

## 行动清单
- [ ] Fix 1: ... — 文件:行
- [ ] Fix 2: ...

## 验收标准
- [ ] self-check 通过
- [ ] monitored build通过
- [ ] 图像/日志/输出符合预期

## Codify（如适用）
- 规则类型: [pattern/incident/rule]
- 适用范围: [哪些模块/场景]
- 规则内容: [一句话]

## AfterAction（如适用）
- 触发原因: [复杂度/弯路/复盘请求]
```

`goal.md` 是 Fix 的行动蓝图，后续步骤依此执行。Codify/AfterAction 是否触发在此确定。

### Step 3: 调用 Neutralize

缺陷修复默认使用 Neutralize 的工作流：

1. 提取证据：错误文本、日志、截图、文件路径、行号
2. 尽量复现问题
3. 定位根因
4. 做最小安全修复
5. 跑相关测试或命令验证
6. 搜索邻近文件和相似调用点
7. 编译/自测验证：

   **自测 (self-check) — 必做：**

   - 构造本地复现条件：缺陷复现所需的环境配置、参数组合。
   - 编写可重复执行的验证脚本，不做一次性手动验证。
     - **传感器相关缺陷** → 必须用三层架构（见下方规则），写入 `PythonAPI/examples/`。
     - **非传感器缺陷** → 单文件 `self_check_<bug-id>.py` 即可。
   - 跑脚本，输出摘要写入 `state.json.self_check_summary`。
   - self-check 脚本是 Fix 交付物，下次同类问题可直接复用。
   - self-check 未完成 → 不能进 Step 3 (Review Gate)。

   **传感器 self-check 三层架构规则（必须遵守）：**

   传感器类缺陷必须拆成三个入口，避免把研发环境搭建逻辑交给测试同事：

   | 文件 | 职责 | 使用者 |
   |------|------|--------|
   | `<bug-id>_<sensor>.py` | 共享检查模块：发现目标 sensor、采集数据、判定结果；**不创建 world/actor** | 研发 + 测试 |
   | `test_<bug-id>_<sensor>.py` | 测试入口：连接现有环境，通过 role_name 或参数找到已有 sensor，运行共享检查 | 测试同事 |
   | `dev_test_<bug-id>_<sensor>.py` | 研发入口：创建最小复现场景、spawn actor/sensor、调用共享检查、cleanup | 研发自测 |

   规则：

   - Layer 1 环境搭建只允许出现在 `dev_test_*` 中。
   - 共享模块和测试入口不能 spawn world/vehicle/sensor。
   - 通过 `role_name` 或显式参数连接三层，不通过硬编码 actor id。
   - 三个文件都放在 `PythonAPI/examples/` 下，并写入 `state.json.self_check_summary`。

   参考实现：

   - 优先搜索 `PythonAPI/examples/` 下已有三层文件：`test_*.py`、`dev_test_*.py` 及对应的共享模块。
   - 若已有真实三层样例 → 按其结构改写；若只有旧式单文件（如 `self_check_<bug-id>.py`）→ 按上表 contract 新建三文件，旧文件的结构可作为处理逻辑参考。

   **编译与长任务监控：**

   - 长时间构建或打包使用 runtime 自带的 monitored execution（如 herdr pane、独立 terminal session 或等价后台任务）。
   - 记录完整 command、cwd、日志路径、最终状态和可选的 `validation_task_ids`。
   - 纯 Python API、配置、文档等短任务可直接运行本地验证命令。
   - 失败时 Fix 未完成，不得进入 Closeout。
   - 编译失败则视为 fix 未完成，不能进入 Closeout。
8. 总结修复、相似问题、剩余风险
9. 对齐 Intake 和 Fix 产物与实际：
   - 更新 `root-cause.md`：如果修复过程中发现根因假设有偏差，修正为实际根因。
   - 更新 `goal.md`：标记已完成和跳过的项。
   - 更新 Breach 页面（`.proposal/repair/<bug-id>/index.html`）：定位结论、修复方案、文件改动与 commit 一致。
   - 如果 Intake 假设被否决（如 FOV 减半→实际是 FaceScale），必须在更新中标注"已否决的原假设"。
   - 更新后同步 LAN 分享目录：`cp .../index.html /media/yhr/2T/carla_images/doc/<bug-id>.html`

### Step 4: Review Gate

验证通过后、提交并推送前，读取共享质量门：

```text
/home/yhr/.agents/repos/agent-skills/references/review-gate.md
```

用本缺陷的 Canon task page、`root-cause.md`、当前 diff、monitored 或本地验证摘要做 review。优先使用跨 runtime reviewer；不可用时执行本地 adversarial review 并说明。

- 有 blocker：停在 Fix，修复后重新验证和 review，不 commit、不 push、不进入 Closeout。
- 无 blocker：把 review 结果写入 Canon task page § Findings / § Evidence / § Timeline，并继续提交推送。

### Step 5: 提交并推送

Review Gate 通过后提交并推送修复分支，失败则停在 Fix，不进入 Closeout。

前置条件：
- 当前分支等于 `state.json.fix_branch` 或用户明确指定的修复分支
- monitored/本地验证已通过，`self_check_summary` 已准备好
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

### Step 6: 条件触发 Codify

只有符合以下任一条件时触发 Codify：

- 同一错误模式在多处出现
- 修复暴露了误读需求或流程级防错规则
- 用户要求“记下来”或“写成规则”
- 规则适合沉淀为 Canon `patterns/` 或 `incidents/`，必要时兼容写入 repo-local `.agent-state/rules/mistakes.md`

### Step 7: 条件触发 AfterAction

只有符合以下任一条件时触发 AfterAction：

- 修复过程复杂或耗时较长
- 走过明显弯路，后续 agent 可能再次踩坑
- 用户要求复盘、修复记录、debug 总结
- 结论值得沉淀给 6 个月后的自己

## Canon promotion

- 更新 Canon task page：记录修复摘要、验证摘要、review 结果、validation task id、commit/MR、构建产物和剩余风险。
- 创建 update card：`/media/yhr/2T/Canon/raw/update-cards/<date>-repair-<bug-id>-fix.md`。
- Codify/AfterAction 的长期结论优先沉淀到 Canon `patterns/` 或 `incidents/`；repo-local 规则文件只作为项目内运行时兼容入口。

## 更新 state.json

```json
{
  "phase": "intake -> fixing -> fixed",
  "goal_path": "<repo_root>/.proposal/repair/<bug-id>/goal.md",
  "fix_summary": "...",
  "self_check_summary": "脚本路径 + 跑完的摘要（研发自测，非 QA 回归）",
  "self_check_script_paths": ["PythonAPI/examples/test_<bug-id>_<sensor>.py", "PythonAPI/examples/<bug-id>_<sensor>.py"],
  "validation_task_ids": ["<bug-id>-package"],
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

`self_check_summary` 是研发自测摘要，不是测试回归结果；如果使用 monitored execution，摘要必须包含 validation task id、最终状态和关键日志结论。

## 完成检查

Fix 完成必须跑 gate 脚本——不再靠 Agent 自己打勾：

```bash
python3 <skill-dir>/scripts/fix_gate.py <bug-id> --json
```

输出 `fix_gate.json`，verdict 三态：
- **pass** — 可以进 Closeout
- **blocked** — 不可进 Closeout，列出缺失项
- **warn** — 可以进 Closeout 但 review 豁免/部分验证不完整

gate 脚本检查 9 项硬条件：worktree 干净、branch 一致、fix_plan.json 存在（已消费 Intake 产物）、monitored 或本地验证通过、review verdict、commit/push 完成、goal.md 存在（Fix 行动计划）、fix_result.json 存在、Canon 已更新。

## Handoff to Closeout

Fix 写入 `fix_result.json`（按 `references/fix_result_schema.md` 的 schema）和 `goal.md`（行动记录 + Codify/AfterAction 决策），Closeout Agent 以此为主源。

`fix_gate.json` 是 Closeout 的入口防线。Closeout Agent 启动第一步读 gate → blocked 则拒绝 → warn 则继续但告知用户风险。
