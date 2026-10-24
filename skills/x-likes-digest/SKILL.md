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
- 本机固定入口：`~/.local/bin/xurl`（官方 release v1.3.4，安装时校验 SHA-256）；定时运行不调用 `npx` 下载。
- 只读探测：`~/.local/bin/xurl --app x-bookmark-ingest -u haoran_yuan /2/users/me`；每次请求最多等待 45 秒，CLI probe 成功后才继续 build；符合备用条件时也可通过 MCP snapshot probe，不能忽略认证/额度失败。
- 邮件发送前必须对 pending manifest 执行 `python3 <skill-dir>/scripts/x_likes_digest.py validate-pending --manifest <pending.json>`；命令失败就停止发送并保留 pending。新 build 在写入前也会执行相同 HTML 安全检查。
- CLI REST 是主路径；MCP 未启动/不可见不阻断正常 CLI。CLI 不存在、不能执行或瞬时传输故障时，备用 `xapi_wiki`（或同账号 `xapi`）的 `get_users_me` + `get_users_liked_posts`。不得用 `get_posts_liking_users`（某帖点赞者）代替当前用户 Likes。
- 401/403、OAuth refresh/授权失败、402 均停止，不换 MCP 绕过。瞬时故障至多一次备用尝试，CLI/MCP 串行，不执行自动登录或重新授权。凭据错误只报告分类，不输出原始诊断或启用 verbose/trace。
- 备用 MCP 用与脚本 `POST_FIELDS/EXPANSIONS/MEDIA_FIELDS/USER_FIELDS` 对应的字段（MCP 使用 `post.fields`），每页最多 100。按最新优先取到已见 ID 或无 next_token，保留 data/includes 和末页 meta；不额外查询单帖/搜索。
- 只使用本轮 CLI 故障后实时获取的备用响应，不复用旧快照。将备用响应聚合为 `<state-dir>/mcp-likes.json`：`{"user":{"id":"<authenticated-id>","username":"haoran_yuan"},"data":[<按页顺序的原始 Likes>],"includes":{"users":[],"media":[],"tweets":[]},"meta":{<末页 meta>}}`。合并 includes 去重；保留 next_token，不能把截断结果改成完整。
- 先 `probe --mcp-source <snapshot>` 验证，再 `build --mcp-source <snapshot>`；后者复用 seen/baseline、HTML、pending 与 mark-sent，不重复 CLI 请求、不使用仅供离线演示的 `--source-json` 发送邮件。已有 pending 优先恢复，禁止重新 build。未取到已见边界且仍有 next_token 时停止并报告 partial。
- MCP 备用同样保留原 45 分钟总预算；工具无法硬设 45 秒时如实记录。
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
