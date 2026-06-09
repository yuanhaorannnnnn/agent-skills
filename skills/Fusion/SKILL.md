---
name: Fusion
description: |
  基于本地代码仓库的深度研究与方案分析 skill。
  当用户需要对某个技术方向进行深度调研、分析实现方案、评估架构决策、
  或做技术预研时触发。触发词包括："帮我调研一下"、"做深度分析"、
  "research on"、"deep dive into"、"方案分析"、"技术预研"、
  "分析一下这个方向"、"研究一下怎么实现"。
  信息源优先级：Canon > 本地代码 > 项目 runtime buffers > 旧 Wiki/外部 web。
  输出：结构化的深度研究报告（Markdown）。

  即使用户没有用上述关键词，只要场景是多源信息综合分析——比如用户说
  "这个技术在我们 codebase 里怎么落地"、"比较一下 A 和 B 两种方案"、
  "分析一下现有的实现"——都应该触发此 skill 而不是泛泛回答。
---

# Deep Research

对给定技术方向进行结构化深度研究，输出可执行的分析报告与推荐方案。

## 核心原则

**Start Wide, Then Narrow Down**：研究必须从广度扫描开始。窄化深入基于扫描证据，不基于先入为主的假设。

**信息源优先级（不可颠倒）**：Canon > 本地代码 > 项目 runtime buffers > 旧 Wiki/外部 web。详见 `references/source-priority.md`。

## 工作流总览

```
Phase 0: Scope ──> Phase 1: Code Explore ──> Phase 2: KB Search
  │                                             ├─ 2.1 Canon
  │                                             ├─ 2.2 Runtime Buffers
  │                                             ├─ 2.3 Old Wiki / Workspaces
  │                                             └─ 2.4 Constraints
  │                                                   │
  │                                                   ▼
Phase 5: Report <── Phase 4: Synthesize <── Phase 3: External
```

Phase 0-4 详细流程见 `references/research-workflow.md`。

## Phase 0: Scope Confirmation

1. 明确研究主题、范围边界、输出深度、硬约束
2. 确认目标代码库（默认当前目录）
3. 判断 effort tier：

| Tier | Phase 1 | Phase 3 | Guardrails |
|------|---------|---------|------------|
| **Light** | 1 grep + 1-2 files | Optional | max 3 file reads, ≤500 words |
| **Medium** | Broad scan + narrow down | Standard (2-3 searches) | max 10 file reads, ≤2000 words |
| **Deep** | Scan + doc-vs-code check | Deep (4-6 searches + cross-verify) | max 20 file reads, ≤5000 words |

**Light**: single function/config query, answerable in 1-2 files, user says "brief".
**Deep**: 3+ files, solution comparison, improvement proposals, user mentions "architecture".
**Medium**: default.

## Phase 1: Local Code Exploration

1. Broad scan: grep/find keywords, read ARCHITECTURE.md/README.md/CLAUDE.md, identify 3-5 relevant modules
2. Narrow down: deep-read 1-2 critical files, trace call chain, record findings
3. Deep tier: doc-vs-code consistency check (DESIGN.md/SPEC.md vs actual implementation)

详见 `references/research-workflow.md` § Phase 1。

## Phase 2: Local Knowledge Base

按优先级检索三层知识体系。搜索命令和源优先级见 `references/source-priority.md`。

1. **Canon**（始终执行）：`rg` 搜索 projects/tasks/patterns/decisions/incidents/artifacts
2. **Runtime Buffers**：MEMORY.md → Canon tasks → conversations → planning → CLAUDE.md → mistakes.md
3. **Old Wiki / Agent Workspaces**（补充源）：Canon 和 repo 信息不足时读取
4. **提取约束**：架构决策、已知问题、技术约束、历史尝试

## Phase 3: External Information

执行强度由 Phase 0 effort tier 决定。搜索策略和深度读取见 `references/research-workflow.md` § Phase 3。

## Phase 4: Synthesis

核心决策点。使用 sequential-thinking（如有 MCP）或显式思考框架。

四个决策点：研究方向评估 → 约束冲突分析 → 方案对比评估 → 信息冲突解决。

不确定性标记、方案对比矩阵、引用验证规则见 `references/research-workflow.md` § Phase 4。

## Phase 5: Output Report

**输出报告前跑 gate**：
```bash
python3 ~/.claude/skills/Fusion/scripts/pre_report_gate.py --evidence .research/evidence.json
```
blocked → 缺证据，补扫 Canon/代码。pass → 继续输出。

研究过程写证据到 `.research/evidence.json`：
```json
{
  "canon_searches": ["rg -i 'keyword' /media/yhr/2T/Canon/..."],
  "canon_matches": 3,
  "code_scans": ["grep -riE 'keyword' src/"],
  "files_read": ["src/foo.py", "src/bar.cpp"],
  "citation_markers_used": ["code_confirmed", "doc_confirmed", "external"]
}
```

报告结构、保存路径、Canon promotion 见 `references/output-format.md`。

## 关键约束

- 信息源优先级不可颠倒。外部最佳实践只有不与本地约束冲突才推荐。
- 不可跳过 Phase 1，即使主题看起来简单。
- 每个结论必须标注来源，不允许无来源断言。
- 跨 agent 兼容：支持有/无 sequential-thinking MCP 两种模式。

## 资源

- `references/research-workflow.md` — Phase 0-4 详细流程、effort tier、sequential-thinking、citation verification
- `references/source-priority.md` — 信息源优先级、Canon 搜索命令、冲突处理规则
- `references/output-format.md` — 报告模板、保存位置、Canon promotion、质量自检清单
