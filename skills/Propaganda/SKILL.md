---
name: Propaganda
description: |
  宣传战工具。将任意话题/长文/想法转成 X thread 打击格式——短句突袭、
  hook 破防、去水分、可 viral。输出为 Markdown，匹配 wiki query 笔记的蒸馏模板。

  Trigger on: "写个 thread"、"X 风格"、"改成推文"、"精简成 thread"、
  "发推格式"、"twitter thread"、"写成 X 帖子"、"用 thread 总结一下"、
  "提炼成 thread"、"宣传一下"、"propaganda"。
---

# Propaganda — X 宣传战

> 信息是子弹。Thread 是弹匣。短句是点射。

## 弹药来源

本 skill 的风格规则提炼自 wiki 中 13+ 篇 X thread/article 蒸馏笔记，覆盖
Boris Cherny、Addy Osmani、Hunter Leath、歸藏、Satya Nadella 等作者的
写作模式。规则随 wiki 新增素材持续演化。

## 作战条例

### 排兵（结构）

1. **Hook 第一条 — 破防**：反直觉观点、数据、或大胆断言。必须让人停下来。
   模式："X 不是 Y，而是 Z"，"something 重新定义了 X"
2. **一条 tweet = 一个弹丸**：不跨条断句，每条独立可转发/可打击
3. **数字编号 `1/ 2/ ... n/n`**：弹匣序号，thread 原生格式
4. **结尾 punchline 或 CTA**：最后一击——总结 / 行动号召 / 邀请接火

### 炼句（句法）

5. **去水分**：删"我觉得"、"interesting"、"very"、"really"、"basically"、
   "just"、"actually"、"simply"——这些都是哑弹
6. **数字优先**：有数据就不用形容词。"200ms" 不写 "很快"
7. **短段落呼吸**：中文 1 句换行，英文 1-2 句换行。控制节奏，不停歇
8. **箭头递进 `→`**：因果链用 `→` 串联，模拟 thread 的"上条推→下条推"推进

### 用语（语言）

9. **中英混排**：技术术语、工具名、命令保留原文，句子结构为中文
10. **反引号包裹**：工具名 `Claude Code`、命令 `/goal`、代码 `read()` 一律内联
11. **保留原话**：关键金句用原文引号嵌套，不意译——原话即原爆点

### 火力（张力）

12. **辩证结构**：before vs after、wrong vs right、old vs new 对仗制造阅读张力
13. **拒绝和稀泥**：有立场，有判断。X 不奖励"一方面...另一方面..."——那是投降

## 输出格式

```markdown
> 🧵 [一句话 thread 主题——hook]

1/ [反直觉核心观点]

2/ [展开 — 为什么是这样 / 数据支撑]

3/ [深入 — 具体案例 / 可操作细节]

...

n/n [Punchline：一句总结 / CTA / 引回 core insight]
```

## 场景适配

| 输入类型 | 处理方式 |
|---------|---------|
| 长文/笔记 | 提取 3-7 条核心要点，每条独立成推 |
| 口头想法 | 先结构化逻辑链，再写成 thread |
| 英文 thread | 保留原文风的中文改写，关键技术词不翻译 |
| 技术深度内容 | "一篇论文一句话" + 3 条为什么重要 |
| 多观点讨论 | 按参与方立论 → 转折点 → 结论分层 |

## 审查

写完自己过三关：

1. **Hook 关**：第一条让人想停下来吗？不是的话重写
2. **转发关**：每条能独立转发吗？不能的话拆开
3. **水分关**：删掉任何一句"我觉得""interesting""very"后意思变了吗？没变就不该有

## Canon 输出边界

读取共享契约：`/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md`。

- 本 skill 为纯风格约束层，通常无 durable artifact。若用户要求将 thread 入库 wiki，
  按 content-ingest 流程写入 `queries/`。
- Canon update-card 路径（需要时）：`/media/yhr/2T/Canon/raw/update-cards/<date>-xwrite-<topic>.md`。
