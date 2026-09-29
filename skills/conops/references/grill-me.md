# Optional simulated review

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
