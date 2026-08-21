---
name: codify
description: |
  Use only when the desired output is one compact, reusable guardrail that
  prevents a mistake from recurring. Trigger on "write this down as a rule",
  "remember this mistake", "capture a lesson learned", or "add a guardrail for
  next time". Do not use for a narrative of one incident or debugging journey;
  use after-action. Do not use for an end-to-end report on a completed task; use
  sanitize report mode.
---

# Capture Mistake Rule

## Artifact Mode

读取共享契约：
`/home/yhr/.agents/repos/agent-skills/references/clean-delivery-contract.md`。
Codify 的错误/正确/触发规则是 `delivery` guardrail，输入必须是已确认的单条可
执行规则。事故叙事、失败尝试和原始讨论属于 `audit`，不复制到规则正文；规则只
描述将被长期执行的最终不变量。

## Boundary

Produce a rule, not a story or report. The minimum useful output is wrong approach, correct approach, trigger, and evidence. If incident chronology matters, route to after-action. If the full task lifecycle and evaluation matter, route to `sanitize report`.

## Workflow

1. Apply the permanence gate before drafting anything. Reject durable storage when the incident is a one-off typo, an obvious local error, or already enforced by compiler/lint/test. Explain which criterion failed; do not invent a generalized rule merely because the user asked to make it permanent.
2. Summarize the qualifying mistake in one sentence.
3. Convert it into a compact rule with:
   - incorrect approach
   - correct approach
   - trigger scenario
4. Check Canon `patterns/` and `incidents/` first, then check repo-local `.agent-state/rules/mistakes.md` for compatibility duplicates.
5. Append the raw incident record if it is materially new.
6. If the rule is reusable beyond one isolated incident, promote it to Canon `patterns/` or `incidents/`; repo-local `.agent-state/rules/mistakes.md` is a project compatibility mirror.

## Quality Gate（写规则前自问）

一条 guardrail 必须同时满足：

- 持久价值：后果显著、结论不显然，且不是 compiler/lint/test 已可靠覆盖的错误
- 触发条件：什么时候会再犯（具体场景，不是“任何时候”）
- 动作：该做什么（可执行命令句，不是“注意/小心/确认”）
- 可检查结果：怎么知道做没做（可被代码、日志或 checklist 验证）

不满足任一 → 不写 guardrail。多步流程交给 pattern / checklist / 脚本工具；
单次事故且无复现证据的教训只记 raw，不 codify。禁止为写规则而写规则：
颗粒度小的伪规则直接丢弃（历史教训：曾因堆积细粒度 rule 造成 guardian/
autoreview 审核量与上下文膨胀）。

参考依据：wiki 仓库 `queries/20260730-codex-custom-code-review-rules.md` 与
`raw/config/20260723-codex-default.rules`（Codex custom rules 优化任务）——
规则只写 consequential、non-obvious 的不变量；删除后 review 结果不变的规则
不值得常驻；能写成测试 / lint / checklist / 脚本的约束，不占规则位。

## Promotion Rule

Promote a mistake into Canon when at least
one of these is true:

- it has happened more than once
- it affects multiple skills or workflows
- it is a process-level guardrail, not just a local typo
- it belongs in the cross-project Canon graph as a long-term rule

Keep one-off or purely local mistakes only as raw incident entries in repo-local `.agent-state/rules/mistakes.md`. Do not elevate them into Canon patterns.

## Canon 输出边界

读取共享契约：`/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md`。

- Durable rules go to Canon `patterns/` or `incidents/`; repo-local `.agent-state/rules/mistakes.md` remains a runtime compatibility mirror.
- For each materially new reusable rule, create or update `/media/yhr/2T/Canon/raw/update-cards/<date>-codify-<slug>.md` with wrong/correct/trigger/evidence.
- If the rule is project-specific only, update the project page or local rule file and state that no cross-project Canon pattern was created.

## Script

Use `<skills-root>/.scripts/note_rule.py` for deterministic repo-local compatibility updates. The script records the raw incident in `.agent-state/rules/mistakes.md`; Canon promotion is the durable step.
