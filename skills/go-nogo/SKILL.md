---
name: GoNogo
description: |
  评估用户描述的功能是否需要新建 skill，还是可用现有工具或已有 skills 实现。
  当用户描述一段功能、说"我想实现..."、"能不能做..."、"这个要不要封装成 skill"、
  "需不需要创建一个 skill"、"帮我评估一下这个功能"、"这个功能用现有工具能做吗"时触发。
  也触发于用户询问某个需求的最佳实现方式，或纠结是否值得投入创建 skill 时。
  核心目标是防止技能膨胀和重复造轮子，给出客观、可执行的建议。
---

# Skill Evaluator

判断一个功能值得封装成新 skill，还是用现有工具/已安装 skill 就能搞定。
在"过度封装"和"该封不封"之间找平衡。

## 评估维度（1-5 分）

| 维度 | 5 分 | 1 分 |
|------|------|------|
| **现有覆盖度** | 已有工具/skill 100% 覆盖 | 完全无覆盖，需从零实现 |
| **复杂度** | 多步状态管理、跨文件、外部 API | 单步操作或简单命令 |
| **使用频率** | 每天/每周多次 | 一次性 |
| **触发清晰度** | 明确的触发词，用户会自然说出 | 意图模糊，或本质是工具链配置 |
| **维护成本** | 依赖易变的外部 API/格式 | 纯逻辑/流程，几乎不需维护 |

## 决策

| 结论 | 条件 |
|------|------|
| 🟢 **创建** | 覆盖度 ≤2 且 复杂度 ≥4 且 频率 ≥4 且 触发 ≥3 |
| 🟡 **创建** | 覆盖度 ≤3 且 复杂度 ≥3 且 频率 ≥3 且 触发 ≥3 |
| 🔵 **扩展现有** | 覆盖度 3-4，已有 skill 能覆盖 60-80% |
| 🔴 **不创建** | 覆盖度 =5 或 (覆盖度 ≥4 且 频率 ≤3) 或 (复杂度 ≤2 且 频率 ≤3) 或 触发 ≤2 |
| ⚪ **需更多信息** | 信息不足以判断频率或复杂度 |

**快速否决**：覆盖度 =5 或 (触发 ≤2 且 复杂度 ≤2) → 不创建，无需完整评估。

## Capability Test

创建前必须回答：新 skill 是否固化了模型无法稳定自行维持的东西？至少满足一项：

- 可重复的多步状态机或外部系统协议
- 明确、可机器验证的 feedback gate
- 稳定的领域契约、schema 或安全边界
- 用户可见的 orchestrator，或被 orchestrator 复用的 discipline/adapter

只有语气、篇幅、普通写作方式、单条提示词或基础模型已稳定具备的能力 → 不创建。优先写入 Global Guidance、Canon domain language、现有 skill 或确定性脚本。

若创建，先声明 `invocation`、`role`、`calls`。`user` skill 负责可见流程；`model` skill 提供可复用能力。避免 user-invoked orchestrator 相互嵌套；必须嵌套时，重新检查 owner 是否重复。

## 输出

```markdown
## 评估结论：[创建 / 不创建 / 扩展现有 / 需更多信息]

### 评分
| 维度 | 得分 | 说明 |
|---|---|---|
| 现有覆盖度 | X/5 | ... |
| 复杂度 | X/5 | ... |
| 使用频率 | X/5 | ... |
| 触发清晰度 | X/5 | ... |
| 维护成本 | X/5 | ... |

### 理由
[2-3 句话]

### 替代方案（如不创建）
[用哪些现有 tools/skills 可以实现]
```

## Canon 输出边界

读取共享契约：`/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md`。

- Go/no-go recommendations can become Canon decisions when the user accepts them. Create an update-card for accepted skill/tooling decisions; otherwise keep the answer ephemeral.
- Canon update-card path, when needed: `/media/yhr/2T/Canon/raw/update-cards/<date>-gonogo-<topic>.md`.
