# Mistake Patterns

## 钉钉周报禁止群发/单聊骚扰

**错误**：提交钉钉周报时加了 `--to-chat` 参数，导致每个接收人收到单聊消息骚扰。

**正确做法**：
- 钉钉周报通过 `dws report create` 提交到日志模块
- 通过 `--to-user-ids` 指定接收人，他们只在日志模块内查看
- **绝对不要加 `--to-chat`**（会发单聊消息给每个接收人）
- **绝对不要用群消息广播周报内容**

**影响文件**：
- `scripts/submit_dingtalk_report.py` — 已移除 `--to-chat`
- `scripts/sunday_finalize.sh` / `scripts/friday_review.sh` — 只设置 `REPORT_RECEIVERS`

**日期**: 2026-06-02
