---
name: Tasking
description: |
  需求开发全流程作战指挥系统。四阶段：Orient(情报分析→方案)、Briefing(上传知识库→评审日程)、
  Engage(状态→开发中→Execute --plan→启动/goal)、Turnover(交付物→系统测试)。
  
  Make sure to use this skill whenever the user:
  - mentions a demand/requirement ID (e.g. JHBN-7712, #1234) and wants to process it
  - says 处理需求、需求开发、写方案、方案评审、开始开发、进入开发、交付、提测
  - asks to upload a design doc to knowledge base or schedule a review meeting for a demand
  - wants to change a demand status to 开发中/系统测试 or post deliverable links
  - uses /Tasking or any of its modes: Orient, Briefing, Engage, Turnover
  
  Do NOT use for: checking personal todos, writing weekly reports, code review, creating new skills,
  general git operations, or translating documents — even if a demand ID is mentioned in passing.
---

# Tasking — 需求开发作战流程

一个 skill，四个 mode。从情报分析到任务移交，全链路自动化。

## 路由

解析第一个参数作为 mode：

| Mode | 触发 | Phase |
|------|------|-------|
| `Orient` | `/Tasking Orient <demand-id> [--base <br>] [--branch <br>]` | 1: 情报分析 |
| `Briefing` | `/Tasking Briefing <demand-id>` | 2: 战情简报 |
| `Engage` | `/Tasking Engage <demand-id>` | 3: 接敌开发 |
| `Turnover` | `/Tasking Turnover <demand-id> --deliverables "<url1> <url2>"` | 4: 任务移交 |

- 参数不匹配任何 mode → 列出用法帮助
- 匹配后立即 Read 对应 mode 文件执行完整流程

## 全局约定

- **需求文档目录**: `/media/yhr/2T/yunxiao/requirements/<demand-id>/`
- **state.json**: 每个需求的状态文件，Phase 0 创建，各 phase 更新
- **phase 值**: `new` → `plan` → `review` → `dev` → `test` → `done`
- **不确定点**: 列出向用户确认，不要假设
- **只读保护**: 不修改 state.json 中自己未负责的字段


## Workflow Gate Contract

Tasking modes must satisfy the shared workflow output contract:

```text
/home/yhr/.agents/repos/agent-skills/references/skill-output-contract.md
```

Each mode must leave a clear phase gate in `state.json`, a Canon task/update-card entry, and durable artifact refs for design docs, review pages, goal.md, deliverables, and status changes.

## Gotchas

- Yunxiao status and user updates require IDs. Resolve status IDs with `get_work_item_workflow`; resolve `樊亮亮` to userId before Turnover assignment.
- `Engage` must go through `Execute --plan` and a real `/goal <goal.md>` or `/loop custom <goal.md>` handoff. Do not inline implementation while claiming Execute launched.
- `Turnover` changes demand status to `系统测试` and assignee to `樊亮亮`; this owner-change rule applies to demand flow only, not Repair.
- Do not create `.planning/conversations/<demand-id>/` as the durable plan. Canon task page is durable state; `goal.md` is runtime execution brief.
- Do not enter Turnover unless build/validation evidence and Review Gate/Traceback results are recorded or explicitly waived.

## Canon 输出边界

读取共享契约：`/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md`。

- `state.json`、`.planning/<demand-id>/`、`.proposal/<demand-id>/` 是阶段门控和执行缓存，不是长期 source of truth。
- 每个需求应在 Canon 中有持久任务页：`/media/yhr/2T/Canon/tasks/<demand-id>.md`，记录当前阶段、关键决策、负责人流转、交付物和下一步。
- 方案文档、知识库 URL、评审日程、`goal.md`、交付物 URL 都作为 Canon artifact refs 记录，默认只引用绝对路径或 URL，不复制文件。
- 每个 mode 完成后，如果产生了新事实，创建或更新 `/media/yhr/2T/Canon/raw/update-cards/<date>-tasking-<demand-id>-<mode>.md`，再把稳定事实合并到 task/project/workflow 页面。
- 如果 Canon 暂不可用，先完成 Yunxiao/state.json 的阶段动作，并在最终回复中明确 Canon promotion 未完成。
