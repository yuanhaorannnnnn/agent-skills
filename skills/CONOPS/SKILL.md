---
name: CONOPS
description: |
  基于 conversation 对话记录、planning 文档和代码变更，生成面向产品、测试、
  开发同事的技术开发设计方案文档（Markdown）。

  触发词："生成开发方案"、"写设计评审文档"、"生成技术方案"、"write design doc"、
  "dev design"、"把这个 feature 的方案整理出来"、"写一个 XX 的技术方案"。

  注意：这不是需求文档或 PRD，而是技术实现方案，重点回答"怎么做"和"为什么这么做"。

  即使用户没有说"开发方案"这四个字，只要场景是"开发前的技术方案编写"——
  比如用户说"整理一下 XX 传感器的设计"、"把 XX feature 的架构写出来"、
  "写个文档给评审会看"——都应该触发此 skill。
---

# Dev Design

基于开发 conversation 生成结构化技术设计方案，面向产品/测试/开发评审。

## 为什么需要这个 skill

开发方案是评审阶段的核心输出物。它需要同时满足三个受众：
- **开发同事**：看架构、核心逻辑、数据模型、代码导航
- **测试同事**：看测试评审点、验收标准
- **产品同事**：看用户可见行为、范围边界、产品评审点

直接让 agent 自由输出容易产出"教科书风格"的泛泛文档。这个 skill 强制按
固定的 14 节结构 + 写作约束执行，确保文档能直接拿到评审会上用。

## 生成前：先做契合检查

方案文档产出的前提是问题定义清晰。在写 14 节文档之前，先确认三件事：

1. **解决什么问题？** — 不是功能描述，是用户痛点。不是「加一个 ToF 传感器」，是「当前 LiDAR 在雨雾天无法测距，仿真测试缺数据源」。
2. **为什么现在做？** — 什么变了？需求、排期、依赖、资源？
3. **怎么算做完了？** — 可验证的终点。不是「传感器能跑」，是「生成的点云帧率和实测传感器误差在 5% 以内」。

如果答案模糊，先和用户对齐再生成文档。这三问的结果反映在方案文档的第 2 节（背景与问题）和第 3 节（方案范围）中。

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

### 文档结构（14 节，强制）

1. **Executive Summary** — 1 句话 + 核心结论 bullet list（面向所有人）
2. **背景与问题** — 为什么需要这个方案，现有能力为什么不够
3. **方案范围** — 本次包含 / 本次不包含（两节等长或"不包含"更长）
4. **用户可见行为** — 从使用方视角描述，分 4 小节：
   - 4.1 Blueprint — 新的 blueprint id、与现有 sensor 的关系
   - 4.2 Python 回调 — 只需说明如何获取数据。必须包含：回调类型、属性访问路径、代码示例
   - 4.3 DFS / Proto 数据 — 新增 message 类型、字段列表、单位约定
   - 4.4 典型配置 — **必须列出所有参数的名称、默认值和含义**（三列表）。读者是上层开发/测试，他们不关心模型内部实现，只关心暴露了什么参数、怎么用
5. **Architecture / Flow** — ASCII 图 + 文字说明（面向开发同事，可以涉及内部实现）
6. **Core Logic** — 关键算法/公式/数据流，读者是开发同事
7. **Protocol And Data Model** — Python API + Proto/DFS + 扩展模型
8. **Product Review Points** — 产品评审建议确认的问题
9. **Test Review Points** — 按层级拆分的测试用例表（编译 → API → Runtime → DFS → 一致性）
10. **Acceptance Criteria** — 可验收的功能清单
11. **Risks And Mitigations** — 风险/影响/应对三列表
12. **Code Navigation** — 文件/职责三列表
13. **Current Status And Next Steps** — 已完成 / 未完成 / 建议下一步
14. **Review Decision Checklist** — 评审会上逐条确认的 checkbox 清单

### 保存位置

设计方案文档保存到**当前工作仓库的** `.proposal/` 目录（与 `.planning/`、`.research/` 平级）。路径相对于研发所在的仓库，不是 agent 平台仓库。

**有 demand/bug ID 时**（从 Canon task page 或用户参数获取）：
```
<cwd>/.proposal/<demand-id>/<Feature> 方案评审文档.md
```

**无 ID 时**（按任务标题 kebab-slug）：
```
<cwd>/.proposal/<task-slug>/<Feature> 方案评审文档.md
```

例如开发 CarlaUE5 的 ToF 传感器时，输出：
```
/media/yhr/2T/CarlaUE5/.proposal/tof/ToF Camera Sensor 方案评审文档.md
```

### Canon 输出边界

读取共享契约：`/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md`。

- `.proposal/` 中的方案文档是评审 artifact，仍保存在当前工作仓库。
- 方案中的长期事实进入 Canon：需求/任务状态、方案决策、接口约束、风险、评审结论、后续任务。
- 生成方案后，创建或更新 `/media/yhr/2T/Canon/raw/update-cards/<date>-conops-<topic>.md`，把方案文档作为 absolute-path artifact ref。
- 若由 `Tasking Orient` 调用，优先更新 `/media/yhr/2T/Canon/tasks/<demand-id>.md`；独立方案则更新对应 project/task/decision 页面。

---

## 模拟评审（grill-me，可选）

文档生成后、交给人评审之前，可选触发一次模拟评审：

```
Interview me relentlessly about every aspect of this plan until we reach
a shared understanding. Walk down each branch of the decision tree,
resolving dependencies between decisions one-by-one. For each question,
provide your recommended answer. Ask one question at a time.
If a question can be answered by exploring the codebase, explore instead.
```

**触发方式**：用户说"先自我评审一下"、"模拟评审"、"grill this plan"。
**输出**：逐条挑战 + agent 推荐回答 + 用户确认/覆盖。修改后的内容回写到方案文档。
**跳过条件**：用户明确说"不用评审，直接发"。

---

## 写作原则

### 面向 API 使用者编写（最重要）

这份文档的主要读者不是模型实现者，而是：
- **上层开发同事**：使用 Python API 调用模型，不关心内部实现
- **测试同事**：基于暴露的参数设计测试用例

因此：
- 典型配置节必须列出**每一个参数的名称、默认值和含义**，缺一不可
- Python 回调节只需要说明"如何获取数据"，给代码示例即可
- 不要说"配置方式沿用 XX 类"，直接给参数表——`depth_format` 是什么？默认值多少？单位是什么？测试同事需要这些来写用例
- 如果参数的含义或用例不清楚，优先补文档，不要让对接方口头来问

### 先保信息，再谈风格

代码路径、配置值、编译参数、proto 字段名、数值、单位 —— 绝对不改。
改写只发生在"包装层"的文字上，不能改变任何一个技术事实。

### 用断言句，不用 hedging

每一句话都能在评审会上直接作为结论使用。

| ❌ | ✅ |
|---|----|
| 当前方案暂未考虑 IR 输出 | 第一版不包含 IR 输出 |
| 建议在后续版本中对性能进行优化 | 第一版不做性能优化。目标：功能闭环 + 数据契约正确 |
| 该传感器能够满足产品侧的基本需求 | 你的产品目标是"可交付的 ToF 点云数据流"还是"完整物理 ToF 仿真"？前者匹配，后者需要另立需求 |

### "本次不包含"比"本次包含"更重要

评审会上被问最多的不是"做了什么"，而是"不包括什么"。"本次不包含"清单
必须比"本次包含"至少等长。每一项都要说清楚为什么不在第一版。

### 不要给产品/测试派活

| ❌ | ✅ |
|---|----|
| 建议产品侧确认是否需要 XX 能力 | 是否接受第一版只输出 point_cloud？IR/Gray 放入后续版本 |
| 测试侧需要加强对 XX 的验证覆盖 | 测试评审建议把验收拆成四层：... |

给产品的是**选择题**，给测试的是**测试用例表**，不是"建议加强"。

### 禁词清单

文档中不得出现以下词汇（来自 Humanizer-zh / 说人话 的总结）：

**短语级禁词**（代表 AI 腔）：
```
此外、值得注意的是、需要强调的是、综上所述、通过...实现、基于...进行、
显著提升、深入探讨、全方位、赋能、助力、在...的过程中、其目的在于、
能够有效地、具有以下优势、不言而喻、不可或缺、重中之重
```

**句式级反模式**：
```
"本方案具有以下显著优势..."
"需要指出的是..."
"建议...，以..."
"通过...的方式..."
"在当今...的时代背景下..."
```

### 数字和文件名前置

每个章节的第一句话应该用具体数字或文件路径开头。

| ❌ | ✅ |
|---|----|
| 该传感器的分辨率参数默认配置为 240x156 | 默认分辨率为 240x156 |
| 深度还原逻辑与已有 RGB-D 的实现保持一致 | 深度还原调用 `DepthImageEncoding::ConvertEncodedDepthToUint16Millimeters()` |

---

## 质量检查（输出前自检）

- [ ] 文档包含全部 14 节
- [ ] "本次不包含"清单长度 ≥ "本次包含"清单
- [ ] 每段第一句能直接回答"这和我的工作有什么关系"
- [ ] 没有禁词清单中的任何词汇
- [ ] 没有"建议..."句式（除了第 8 节产品评审点）——第 8 节用选择问句
- [ ] 测试评审点按层级（编译 → API → Runtime → DFS → 一致性）拆分
- [ ] 风险表中有具体文件路径或参数名
- [ ] Code Navigation 表中每行都有文件路径 + 职责描述
- [ ] 全文不超过 10 个"需要"、8 个"建议"、5 个"后续"
- [ ] 文件已保存到 `.proposal/<demand-id>/` 或 `.proposal/<task-slug>/`，不按 conversation id 建目录
- [ ] Canon update-card/task/decision/artifact refs 已记录，或明确说明本次只生成临时方案 artifact

---

## 参考

- [人类化中文写作指南](https://github.com/op7418/Humanizer-zh) — 24 种 AI 写作痕迹
- [说人话](https://github.com/MrGeDiao/shuorenhua) — 210+ 中文禁词、19 种反模式、保真回读
- 本地反例对照：见 `references/taste.md`
