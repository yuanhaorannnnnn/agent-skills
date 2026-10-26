# Global Agent Guidance

## 沟通

用简体中文；technical terms、标识符、命令、路径和代码保留英文。省套话、冠词、客套和冗余缓和语；优先短语、短词和箭头，安全警告、不可逆操作与设计文档用完整句子。
英文仅纠正歧义、语义颠倒、关键术语误用或无法理解的问题，忽略小错；需纠正时末尾只加一行：
`> 💡 "your version" → "suggested version"`

## 协作中的理解与决策

- 从用户表达中识别本轮主要追求交付、验证还是探索；可并存，不要求用户选模式或填表。仅澄清会改变行动的歧义。
- 关键假设被推翻、路线分叉、交付范围变化，或连续迭代未推进目标时，及时说明：什么证据改变了认识、对目标的影响、下一步为何值得做。区分局部任务完成与整体目标进展；不按每个工具调用机械汇报。
- 授权范围内的调整说明后继续；改变目标、验收或显著追加投入时，给出具体选项、代价和建议，复用已有授权，仅等待缺失的决定，不阻塞独立工作。用户可随时追问目的、要求演示或调整探索偏好，无需专门命令；状态追问不等于停止工作。
- 用最能帮助判断的证据说明变化（短解释、图、演示或对照），不默认增加长报告、审批或新文件。持久任务复用 Canon 当前状态；理解是否改善由实际协作反馈判断，不以字数、报告数或 gate 通过代替。

## 上下文与按需规则

- Canon：`/media/yhr/2T/Canon`。依赖项目决策、任务状态或跨仓库背景时先查，优先于 `.agent-state/`；单仓库、自包含、可逆且不改公开/安全/数据契约或外部状态的修改可直接做，无需查 Canon 或新建 task。改变长期决策或需交接的结果回写 Canon。
- Wiki：`/media/yhr/2T/files/wiki`，仅作参考知识库。
- 下列 reference 位于 `/home/yhr/.agents/repos/agent-skills/references/`，仅满足条件时读取：
  - 找回历史总结/结论 → `canon-output-contract.md` 的 Historical recall；索引优先、原文核实，不凭记忆重建。
  - 实证技术预研（可行性、归因、模型选择、拟合/标定）→ 选数据/观测代理、定实验或搜索参数前读 `research-admission.md`；无需 Conops，普通问答/忠实翻译摘要/归档不触发。
  - skill 产生 pass/blocked/skipped/error → 按 `skill-telemetry.md` 发一次本地事件；只记允许的元数据，失败不改变任务结果。
- 技能中的 `<skill-dir>` 是实际加载的 SKILL.md 所在目录，`<skills-root>` 是其父目录，不替换成猜测的 runtime 路径。
- 上下文换会话：新建对话，用 passdown 并读其 rollover 规则；不 resume/fork 旧 transcript，`/compact` 不重置 Guardian。

## 邮件交付

- 用户明确要求某个任务完成后发邮件时，读取 `/home/yhr/.agents/repos/agent-skills/references/automation-runtime.md` 的“按任务启用的完成邮件”，复用现有投递防重与回执机制。邮件含结果、关键限制、手机可读成果入口，草稿明确标识；邮件回复不自动触发 agent。没有该任务发送授权时仍在当前聊天交付。

## Prompt 调用

用户明确输入 `&<名称>` 时，读取当前用户 `~/.agents/prompts/<名称>.md`，作为当前对话的附加指令。只接受单个文件名，不接受路径；缺失就说明，不猜正文。

## 操作约束

- 只读检查先用当前 sandbox；`rg`、`sed -n`、`jq`、`wc`、`nl`、`find` 和普通读取不预先提权。仅本轮发生具体 sandbox/网络拒绝后才可申请 `require_escalated`，理由引用该失败。
- Auto-review 过多应修正 sandbox 边界、缩小 `writable_roots`；不得为少弹提示添加宽泛命令放行规则。
- Headless 视觉验证：每版 artifact 合并所有 viewport/截图一次检查，仅发现具体视觉缺陷或后续改版才重跑。
- Worktree 以 `git worktree list` 为准，统一 `<repo>/.worktrees/<safe-branch-name>`；Claude 的 WorktreeCreate/WorktreeRemove hooks 也指向这里，不长期用 `.claude/worktrees/`。本地 scratch 分支不推送；repair/tasking 指定的 `bugfix/*`、`feature/*` 等工作流分支过 gate 后可推送。
- GitHub 操作跨 runtime/provider 默认用本机 `gh`；可用时不改走远端插件、Web connector 或 MCP wrapper。
