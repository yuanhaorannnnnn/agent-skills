# fix_result.json Schema

Fix Phase 输出契约——Closeout Agent 只读这份 JSON 了解修复结果。

## Schema

```json
{
  "bug_id": "JHBN-7712",
  "verdict": "fixed | partial | not_fixed | false_positive | transferred",
  "fix_summary": "一句话修复摘要",
  "root_cause": {
    "confirmed": true,
    "actual_cause": "实际根因（修复后可能修正 Intake 的假设）",
    "differs_from_intake": false
  },
  "changes": {
    "files_modified": ["path/to/file.cpp"],
    "lines_changed": 12,
    "strategy_used": "surgical | refactor | workaround | revert"
  },
  "verification": {
    "self_check_passed": true,
    "self_check_summary": "自测结果",
    "validation_task_ids": ["<bug-id>-package"],
    "validation_final_status": "PASS | FAIL | TIMEOUT"
  },
  "review": {
    "verdict": "passed | blocked | skipped",
    "summary": "review 结论",
    "blockers_resolved": 0
  },
  "delivery": {
    "commit_sha": "abc123",
    "pushed_branch": "bugfix/JHBN-7712",
    "mr_url": "https://..."
  },
  "side_effects": {
    "similar_issues_found": 0,
    "codify_triggered": false,
    "codify_rule_path": null,
    "after_action_triggered": true,
    "after_action_path": "/path/to/after_action.md"
  },
  "risks": ["剩余风险1", "剩余风险2"]
}
```

## Gate 行为

| 字段 | 值 | gate |
|------|-----|------|
| `verification.self_check_passed` | `false` | blocked |
| `verification.validation_final_status` | `FAIL` or `TIMEOUT` | blocked |
| `review.verdict` | `blocked` | blocked |
| `delivery.commit_sha` | null/空 | blocked |
| `delivery.pushed_branch` | null/空 | blocked |
| `review.verdict` | `skipped` | warn ("review 豁免，质量风险自行承担") |
