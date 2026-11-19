---
name: my-dou
description: "读取本人豆瓣账号数据：观影/读书/音乐/游戏标记（看过/在看/想看）、短评、影评、我加入的小组、我的豆列。当用户问『我看过什么/我的豆瓣记录/我的收藏/我在看什么/我加入的小组』或要求统计、整理、导出自己的豆瓣足迹时使用。只读，不写标记、不评分、不发评论。"
metadata:
  requires:
    bins: ["douban"]
  cliHelp: "douban help"
---

# 豆瓣个人数据

本机 `douban` CLI 通过豆瓣 App 接口读取账号数据。**只读**：不会标记、评分、发评论、改豆列。

## 授权（只做一次）

用户第一次使用时，让他自己取 cookie 并灌入 CLI，**不要把 cookie 贴到聊天里**。三种给法，A/B 最省事：

```bash
# 方案 A：Chrome 控制台执行 document.cookie，复制结果后
xclip -selection clipboard -o | douban auth

# 方案 B：Network 面板右键请求 → Copy as cURL，复制后
douban auth --curl '<粘贴整条 cURL>'

# 方案 C：已有字符串
douban auth --cookie '<cookie>'
```

cookie 需要 `bid`、`ck`、`dbcl2` 三项（`dbcl2` 形如 `"123456:xxxx"`，uid 从里面解析）；其余统计类 cookie 带不带都行。授权成功会打印 `✅ 授权成功：<昵称> (<uid>)`，cookie 存到 `~/.config/douban-cli/cookie`（0600）。

之后所有命令自动复用。检查状态：

```bash
douban auth --status
```

失效时重跑一次授权命令；不要尝试账号密码登录，也不要索要密码。

**已知坑（不要重复踩）**：`frodo.douban.com/api/v2/~me` 即使 cookie 完全有效也固定返回 `403 need_login`，不能用作登录校验。CLI 已改为从 `dbcl2` 解析 uid，再用只有登录态才可见的 `people/<uid>/doulists/all` 页面确认 cookie 有效。

## 命令

| 需求 | 命令 |
|---|---|
| 我是谁 | `douban whoami` |
| 看过的电影 | `douban marks --type movie --status done` |
| 在看 | `douban marks --type movie --status doing` |
| 想看 | `douban marks --type movie --status wish` |
| 读过的书 | `douban marks --type book --status done` |
| 听过的音乐 | `douban marks --type music --status done` |
| 玩过的游戏 | `douban marks --type game --status done` |
| 全部记录（自动翻页） | `douban marks --type movie --status done --all` |
| 我写的影评/书评 | `douban reviews --type movie --limit 20` |
| 我加入的小组 | `douban groups` |
| 我的豆列 | `douban doulists` |
| 机器可读 | 任意命令加 `--json` |
| 看别人公开记录 | 加 `--user <uid>` |
| 调试接口 | `douban raw --path /api/v2/xxx --query k=v` |

默认表格输出，含日期、标题、我的评分（1–5 星）、短评、豆瓣 id。`--json` 返回结构化对象，字段：`id/title/year/rating/status/comment/tags/date/subtitle/url`。

## 呈现规则

- 用户问「我看过什么」这类开放问题时，先给 `--limit 20` 的概览，再问是否需要全量 / 按年份 / 按评分筛选。
- 统计类需求（「我看过多少部」「评分分布」「哪年看最多」）用 `--all --json` 拿全量后本地聚合，不要反复分页调用。
- 引用具体影片时带上豆瓣 id 和链接，方便用户点开核对。
- 输出不要暴露 cookie 内容，也不要打印 `~/.config/douban-cli/cookie`。

## 边界

- 只读；写操作（标记/评分/短评）本 CLI 不支持，用户提出时说明限制。
- 频率：CLI 内置 180ms 间隔，全量翻页时仍是数十次请求；不要并发跑多个 `--all`。豆瓣对高频访问会要求登录或限流，遇到连续失败先停手，隔一段时间再试。
- 小组与豆列走网页 HTML（需登录态）：小组页是 `www.douban.com/group/people/<uid>/joins`，豆列是 `people/<uid>/doulists`（301 跳到 `/doulists/all`）。这两页最容易因豆瓣改版失效，`--json` 拿不到数据就先用 `douban raw` 验证接口，再改解析。
- 影评接口只返回长评；没写过长评的账号返回空表，属正常，不要当成接口坏了。
- 数据只在本机流转：接口调用直连 douban.com，无第三方中转、无遥测。
