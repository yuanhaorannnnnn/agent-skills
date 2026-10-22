---
name: conops
description: |
  技术方案内容流程：从对话、planning 和代码起草开发前技术设计，说明架构、取舍与验证。触发于"生成开发方案"、"写设计评审文档"、"技术方案"、"write design doc"，或明确要求整理 feature 架构供评审；md/html/both 不影响触发。HTML 呈现交给 breach；不因测试报告或讨论串采用 HTML 而触发。不用于需求文档或 PRD。
---

# Dev Design

基于开发 conversation 生成结构化技术设计方案，面向产品/测试/开发评审。

## 职责边界

`conops` 是技术方案内容流程，`breach` 是通用 HTML 呈现层；两者按职责组合，不按内容主题互斥分类。只有任务确实要求形成技术方案时启用 `conops`，选择 `md | html | both` 不改变这一条件。测试报告、讨论串都可以用 HTML 呈现，其格式本身不调用 `conops`。

## 为什么需要这个 skill

开发方案是评审阶段的核心输出物。它需要同时满足三个受众：
- **开发同事**：看架构、核心逻辑、数据模型、代码导航
- **测试同事**：看测试评审点、验收标准
- **产品同事**：看用户可见行为、范围边界、产品评审点

按问题复杂度组织文档，遵循 `paperwork` 的读者任务、信息关系和证据校准原则。章节数量、字数和词语不替代工程判断。

## 生成前：先做契合检查

方案文档产出的前提是问题定义清晰。在写文档之前，先确认三件事：

1. **解决什么问题？** — 不是功能描述，是用户痛点。不是「加一个 ToF 传感器」，是「当前 LiDAR 在雨雾天无法测距，仿真测试缺数据源」。
2. **为什么现在做？** — 什么变了？需求、排期、依赖、资源？
3. **怎么算做完了？** — 可验证的终点。不是「传感器能跑」，是「按已批准工作负载、观测定义和误差预算验证点云输出；预算未定则明确待决」。

未知项写入待决清单，继续能独立完成的设计；只有影响方案选择的必要信息才询问用户。涉及拟合、标定、经验规律或物理归因时，先读 `/home/yhr/.agents/repos/agent-skills/references/research-admission.md`，在提出参数搜索前完成观测与可辨识性准入。

## 输入源优先级

dev-design 通常在代码开发之前执行，因此代码不是主要输入源。
优先级按实际可用性排列：

1. **当前对话中的设计讨论** — 所有方案决策、trade-off、参数取舍都在这里。
   这是最丰富的信息源，不要只依赖文件而忽略对话。
2. `/media/yhr/2T/Canon/tasks/<task>.md` — Canon task page 中的 § Plan / § Findings /
   § Decisions / § Artifacts。包含架构决策、约束和 artifact 路径。
3. `.planning/conversations/<id>/` — runtime scratch buffer（spec / task_plan /
   findings / progress）。历史参考，不作为 durable truth。
4. `.agent-state/conversations/<id>.md` — 历史 runtime recap，补充参考。
5. **代码 diff / 参考实现**（可选）— 仅在已有部分代码或参考文件时使用，
   例如 Code Navigation 节需要具体文件路径时。

**如果 Canon task page 或 planning 文档不存在**，直接基于当前对话生成，
并标注缺失的信息源。不要因为文件缺失而拒绝生成。

---

## 输出

### 内容检查表（按读者任务合并、删减或改名，不要求固定章节）

1. **Executive Summary** — 1 句话 + 核心结论 bullet list（面向所有人）
2. **背景与问题** — 为什么需要这个方案，现有能力为什么不够
3. **方案范围** — 本次包含 / 本次不包含（只列实际边界，不按条数配平）
4. **用户可见行为** — 从使用方视角描述入口、操作流程、API/CLI/UI
   变化、配置项、默认值和兼容性。只写当前 feature 实际存在的接口；不要
   强制虚构 Blueprint、Python、Proto 或其他技术栈。
5. **Architecture / Flow** — 必要的图 + 文字说明（面向开发同事，可以涉及内部实现）
6. **Core Logic** — 关键算法/公式/数据流，读者是开发同事
7. **Protocol And Data Model** — 公开接口、schema、状态、单位、兼容性；没有
   相关变化时可省略
8. **Product Review Points** — 产品评审建议确认的问题
9. **Test Review Points** — 按层级拆分的测试用例表（选取实际适用层级）
10. **Acceptance Criteria** — 可验收的功能清单
11. **Risks And Mitigations** — 风险/影响/应对三列表
12. **Code Navigation** — 文件/职责三列表
13. **Current Status And Next Steps** — 已完成 / 未完成 / 建议下一步
14. **Review Decision Checklist** — 评审会上逐条确认的 checkbox 清单

### Variant References

- CARLA sensor 方案 → 确定接口、数据和测试契约前，完整读取
  `references/carla-sensor-design.md`。
- 其他领域 → 按上述内容检查表组织，只保留该领域真实存在的接口、数据模型和
  测试层级。

conops owns content scope, evidence, acceptance criteria, and review decisions.
If the user requests an OpenAI Template or native document, complete this content
contract first, then use the requested template only for final rendering.

### 输出格式：`md | html | both`

默认 `md`；按用户或调用方选择交付格式。自然语言“只要 HTML”“HTML 评审页”等未要求 Markdown 的表达选择 `html`；明确要求两种格式选择 `both`。主题或 `content-mode` 匹配本身不新增 HTML。

- `md`：完成内容契约，保存并校验 Markdown，交付 Markdown。
- `html`：完成并核准同一内容契约，调用 `breach` 的 General page mode，直接保存并校验 HTML，交付 HTML。无需先落盘或额外交付 Markdown。
- `both`：共享一份核准正文；Markdown 是维护源，HTML 是派生呈现。两份均校验；正文更新时重新生成 HTML，避免独立修改造成分歧。

向 Breach 传递已核准正文（不要求 Markdown 文件）、目标项目、输出路径与内容模式：技术方案默认 `research-explainer`；主要交付为状态/验收数据时用 `status-or-benchmark`；用户明确要求专题式封面时才用 `release-or-concept-feature`。Breach 负责目标项目的 `DESIGN.md`、布局、渲染和 provenance；Conops 仍负责事实、范围与验收。视觉隐喻不得替代架构图或测试证据。目标项目没有 `DESIGN.md` 时，沿用 Breach 的参考设计选择流程，不默认引用 Wiki 规范。

HTML 保留所选内容与证据边界，用语义标题、列表和表格组织；不要求固定章节或范围条数。正文写入静态 HTML。渲染不得删减决定方案可行性的约束。

### 保存位置

设计方案保存到当前研发仓库。先读取该仓库 AGENTS.md 和文档布局规则；明确的项目规则优先于本技能默认路径。

- CARLA：按 `Docs/guides/documentation.md` 保存到 `<repo-root>/Docs/tasks/<task-or-demand-slug>/design.md`，与同一任务的研究、执行和验证材料聚合。
- 没有项目布局规定：保存到 `<repo-root>/.proposal/<task-or-demand-slug>/<Feature> 方案评审文档.md`。

上述路径为 Markdown 默认位置；HTML 使用同一任务目录的 `index.html`，用户或项目明确规定路径时优先。`html` 模式只创建 HTML；`both` 在同一任务目录保存两份。已有任务文档时更新所选格式的对应文件，保留归属与创建来源。路径属于研发仓库，不属于 agent 平台仓库。

### Canon 输出边界

读取共享契约：`/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md`。

- 按项目规则解析位置的方案文档是评审 artifact，仍保存在当前工作仓库。
- 方案中的长期事实进入 Canon：需求/任务状态、方案决策、接口约束、风险、评审结论、后续任务。
- 生成方案后，创建或更新 `/media/yhr/2T/Canon/raw/update-cards/<date>-conops-<topic>.md`，把方案文档作为 absolute-path artifact ref。
- 若由 `tasking Orient` 调用，优先更新 `/media/yhr/2T/Canon/tasks/<demand-id>.md`；独立方案则更新对应 project/task/decision 页面。

---

## 模拟评审（可选）

仅用户要求模拟评审时读取 [grill-me 流程](references/grill-me.md)。

## 写作原则

### 面向使用者编写（最重要）

这份文档的主要读者不是内部实现者，而是调用方、测试和产品评审者。

因此：
- 所有公开配置项列出名称、默认值、含义和单位；没有公开配置时明确写无
- API/CLI/UI 用法给最小可运行示例，不展开无关内部实现
- 不要写"沿用 XX"来省略契约；把调用方需要的信息直接列全
- 参数、行为或验收不清楚时标为 open question，不编造默认值
- CARLA sensor 的 Blueprint/Python/DFS 专用要求只来自
  `references/carla-sensor-design.md`

### 先保信息，再谈风格

代码路径、配置值、编译参数、proto 字段名、数值、单位 —— 绝对不改。
改写只发生在"包装层"的文字上，不能改变任何一个技术事实。

### 结论强度匹配证据

区分事实、推断、建议和待决项；没有观测就不写“已验证”。断言语气不能消除不确定性。
范围只写真实纳入项与有争议的排除项，解释边界的原因；不为凑数扩充排除清单。

### 不要给产品/测试派活

| ❌ | ✅ |
|---|----|
| 建议产品侧确认是否需要 XX 能力 | 是否接受第一版只输出 point_cloud？IR/Gray 放入后续版本 |
| 测试侧需要加强对 XX 的验证覆盖 | 测试评审建议把验收拆成四层：... |

给产品的是**选择题**，给测试的是**测试用例表**，不是"建议加强"。

### 表达服务于论证

删低信息量套话；保留准确的限定词、来源原文和技术术语。章节开头回答读者的问题，不强制数字或路径开头。不要用机械禁词或字数阈值评价内容。

## 检查与评审

对最终保存文件运行结构 lint；`html` 检查 HTML，`both` 分别检查两份：

```bash
python3 <skill-dir>/scripts/quality_gate.py <path/to/design_doc.md-or-index.html> --json
```

为兼容调用方保留脚本名与 `verdict`/`failed` 字段。`pass` 仅表示文件可读且有非标题、非占位正文，**不表示设计通过**。`check_kind=structure_lint`、`semantic_review=required` 必须随结果保留。空文件、全占位骨架或不可读文件 blocked；不检查固定章节、范围条数或禁词。HTML 提取静态文本，不计算 CSS 可见性；视觉仍按 Breach 校验。

另行完成语义评审并记录依据：
- 约束 → 选择 → 机制 → 失败路径 → 可执行验收是否闭合？
- 关键结论对应什么来源？反例或代价是否改变选择？
- 验收是否区分确定性不变量、硬运行边界和有噪声的比较？未知预算不得自行填值。
- 研究任务是否满足观测语义、可辨识性、最小判别对照？未满足则限制结论或停止拟合。
- 未决项及其阻塞范围是否明确？Canon 状态是否与实际证据一致？

评测覆盖回复草稿与真实保存文件两条路径；保存文件用例必须执行 lint、保留原始输出，再单独判断方案质量。不得将脚本 `pass` 当成评测 oracle。

---

## 参考

- [人类化中文写作指南](https://github.com/op7418/Humanizer-zh) — 24 种 AI 写作痕迹
- [说人话](https://github.com/MrGeDiao/shuorenhua) — 210+ 中文禁词、19 种反模式、保真回读
- 本地反例对照：见 `references/taste.md`
