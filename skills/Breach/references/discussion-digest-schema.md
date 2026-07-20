# Discussion Digest Intermediate Format

Phase 1 输出——讨论分析的结构化 JSON。此文件既是 schema 也是 Phase 2 渲染器的输入契约。

## Schema

```json
{
  "title": "讨论标题",
  "source_id": "GitHub Issue #42 / X Thread @user / Email Thread Re: topic",
  "source_url": "原始讨论链接",
  "participant_count": 8,
  "message_count": 24,
  "date_range": "2026-06-01 — 2026-06-08",
  "tldr": "1-2 句话核心结论",

  "participants": [
    {
      "name": "显示名",
      "role": "OP | Core | Reviewer | Commenter | Observer",
      "initial_stance": "初始立场（可简短）",
      "final_stance": "最终立场或 changed/unchanged",
      "representative_quote": "一句最能代表其立场的发言（原文）",
      "rationale": "为何持此立场"
    }
  ],

  "timeline": [
    {
      "date": "2026-06-01",
      "author": "发言者",
      "text": "发言内容摘要",
      "is_key": true,
      "why_key": "Pivotal question / New evidence / Framework shift / Participant change"
    }
  ],

  "decisions": [
    {
      "status": "decided | leaning | stalled",
      "summary": "决议内容",
      "detail": "详细说明",
      "icon": "✅ | 🔧 | 🚫 | ⚠️ | 📋"
    }
  ],

  "unresolved": [
    "未解决的问题 1",
    "未解决的问题 2"
  ],

  "action_items": [
    "待办 1 @负责人",
    "待办 2"
  ]
}
```

## 字段约束

- `participants[].role` 必须是枚举值
- `timeline` 最多 30 条，`is_key` 条目 ≤ 8 个
- `decisions` 至少 1 条（没有决策也要写"无明确结论"）
- `unresolved` 不能空——没有就是 `["无"]`
- 所有 `name`/`author` 使用原始显示名，不翻译
