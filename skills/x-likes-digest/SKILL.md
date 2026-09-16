---
name: x-likes-digest
description: 读取 X/Twitter 账号新增的 Likes，按当周实际内容生成一封偏娱乐的 HTML 周报并发送到 Gmail。触发于“处理本周 X 点赞”“X likes 周报”“把最近点赞发我邮箱”；不摄入 Wiki，不点赞或取消点赞，也不用于单个已给 URL 的普通摄入。
---

# X Likes 娱乐周报

把 X Likes 当成每周一次的娱乐 inbox。只做增量发现、分组、排版和邮件投递；不写 Wiki，不调用 acquisition。

## 固定边界

- X 侧只读：只读 `liked_tweets`，不得点赞、取消点赞、发帖、书签或修改任何 X 状态。
- 凭据只由 `xurl` 的 OAuth 配置管理；不得输出 token、secret 或授权头。
- 不写 `/media/yhr/2T/files/wiki`，不执行 git、catalog、index 或 log。
- 收件人固定为 Gmail `me`；不抄送、不转发给其他人。
- 用户已确认的内容规则：按当周实际内容分组，不设固定分类比例；不加点评；视频只给链接，不嵌缩略图；不过滤条目。
- 安全边界：敏感、成人或明显冒犯条目仍保留在周报中，但邮件正文不复述其文本或媒体，只显示“⚠️ 敏感内容，点开原帖查看”加链接。

## 依赖

- `xurl` app `x-bookmark-ingest`，当前 OAuth 已具备 `like.read`。
- 只读探测：`npx -y @xdevplatform/xurl --app x-bookmark-ingest /2/users/me`
- MCP 的 X 工具没有“读取自己 likes”的接口，必须用 xurl REST；不要用 `get_posts_liking_users` 代替。
- Gmail 发送：
  `gmail_send_email({to:"me", subject, payload:{mime_type:"text/html", charset:"UTF-8", body:{content:html}}, response_fields:["id","thread_id"]})`

## 状态

- `~/.codex/automations/x-likes/state.json`
- `~/.codex/automations/x-likes/issues/<issue-id>/`
- `~/.codex/automations/x-likes/memory.md`

`state.json` 的 `seen` 是增量账本；首次运行且没有 `baseline_at` 时只建立 baseline，不发邮件。

Baseline 只关心“从现在往后的新增”。不要自动运行高消耗的 API baseline；优先让用户从 X 设置下载数据归档，用 `import-archive --path <like.js>` 直接导入历史 like 的 tweetId，零 API 读取。没有归档时报告 blocked 并停止，等用户明确同意再建立 API baseline；API baseline 最多读取一页 100 条，增量遇到已见条目即停止。

如果用户手动指定某条推文作为本期起点，用 `set-start --tweet-id <id> --manifest <pending.json>` 建立边界：该推文及更新的 Likes 视为本期新增，之后的旧 Likes 标记为已见。

## 运行流程

1. `python3 <skill-dir>/scripts/x_likes_digest.py probe`
2. `python3 <skill-dir>/scripts/x_likes_digest.py status`
3. 没有 baseline：优先从 X 数据归档执行 `import-archive --path <like.js>`；没有归档就报告 blocked，不自动跑 `baseline --recent 1000`
4. 有 baseline：`python3 <skill-dir>/scripts/x_likes_digest.py build`
5. 按生成的 `pending.json` 逐 part 用 Gmail 发送；subject 为 `X 瞎看 · YYYY.MM.DD`，多 part 时加 `(1/2)`。
6. 每个 part 发送成功后执行 `mark-sent --issue <issue-id> --part <n> --gmail-id <id>`。
7. 报告 `discovered`、`sent`、`parts`、`gmail_ids`、`remaining` 和本地 HTML 绝对路径。

## 邮件规则

- 分组按实际内容：图片 / 视频 / 文字 / 长文 / 外链；空组省略；不按固定配额。
- 图片：每帖最多嵌入 2 张；超过显示“+N 张，点原帖看全”。
- 视频：只显示 `▶ 视频 · 时长 · 看原帖`，不嵌缩略图。
- 长文：最多 160 字加原帖链接。
- 不过滤条目；敏感条目只保留链接和警告，不复述正文或媒体。
- 单封最多 60 条或 HTML 不超过 95KB；超过则分 part，避免 Gmail 裁剪。

## 完成门槛

- `state.json` 已更新 `last_success_at` 和已发送 post IDs。
- 每封邮件都有 Gmail message id。
- 没有 Wiki 或 git 改动。
- 静态配置成功不等于 API 或邮件端到端成功；以 Gmail 返回的 message id 为准。
