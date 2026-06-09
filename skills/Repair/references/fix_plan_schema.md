# fix_plan.json Schema

Intake Phase 输出契约——Fix Agent 只读这份 JSON，不读自由格式 fix_plan.md。

## Schema

```json
{
  "bug_id": "JHBN-7712",
  "summary": "一句话缺陷描述",
  "reproduction": {
    "steps": "复现步骤",
    "env": "环境信息",
    "is_complete": true
  },
  "root_cause": {
    "confidence": "high | medium | low | speculative",
    "files": ["path/to/file.cpp"],
    "lines": ["42", "128-135"],
    "hypothesis": "根因假设一句话"
  },
  "fix_plan": {
    "strategy": "surgical | refactor | workaround | revert",
    "modified_files": ["path/to/file.h", "path/to/file.cpp"],
    "estimated_lines": "<50 | 50-200 | >200",
    "verification_command": "命令或步骤"
  },
  "uncertainties": [
    {
      "question": "不确定的问题",
      "impact": "blocking | clarifying"
    }
  ],
  "related_code": [
    {
      "file": "path/to/related.cpp",
      "how": "caller | callee | similar pattern | config"
    }
  ],
  "attachments": [
    {
      "path": "/media/yhr/2T/yunxiao/bugs/<bug-id>/screenshot.png",
      "type": "screenshot | log | video",
      "description": "说明"
    }
  ]
}
```

## Gate 行为

| 字段 | 值 | gate |
|------|-----|------|
| `root_cause.confidence` | `speculative` | blocked |
| `uncertainties[].impact` | `blocking` | blocked |
| `uncertainties[].impact` | `clarifying` | warn |
| `reproduction.is_complete` | `false` | blocked |
