# Acquisition route: article pipeline

## 文章管线

### Step A0-WeChat album discovery：公开专辑

`/mp/appmsgalbum` 是文章清单，不是文章正文。仅当用户要求“查看/列出专辑”时，
执行 discovery-only：只发现、规范化和去重单篇 `/s?...` URL，不抓取文章、不写 query。
默认按最新优先返回全部文章；`--limit` 只限制输出/manifest 中的待选 URL，不改变完整性检查。

```bash
python <skill-dir>/scripts/discover_wechat_album.py "ALBUM_URL"
```

只看最新 10 篇：

```bash
python <skill-dir>/scripts/discover_wechat_album.py "ALBUM_URL" --limit 10
```

取最早 10 篇：

```bash
python <skill-dir>/scripts/discover_wechat_album.py "ALBUM_URL" \
  --order oldest --limit 10
```

对需要保留或审核的清单，显式写入 manifest：

```bash
python <skill-dir>/scripts/discover_wechat_album.py "ALBUM_URL" \
  --save-manifest --wiki-root /media/yhr/2T/files/wiki
```

manifest 保存为 `raw/collections/YYYYMMDD-wechat-album-<album-id>-<hash>.json`，包含
专辑标题、声明篇数、发现篇数、是否完整、去重数量、选择参数和 article URL。发现篇数少于声明篇数时
`complete: false`；停止并报告，不得对不完整清单启动批量摄入。

#### 专辑摄入：raw → 每篇 query

当用户要求“处理/摄入专辑”时，这个路由进入完整 Acquisition 管线；query 是默认交付物，
不需要额外说“生成 query”：

1. 用 `discover_wechat_album.py` 完整发现并显式保存 manifest；专辑摄入必须提供
   `--limit N`，`--order` 默认 `latest`。未给数量时，先询问，避免把整张专辑当作默认批量任务。
2. 仅在 `complete: true` 时，按 manifest 的 `items` 顺序逐篇执行 Step A1；每篇独立通过
   标题/正文 gate，失败才走一次 WeChat fallback。
3. 每个成功 raw archive 都生成**一篇独立 query**，遵守 [笔记输出格式](../SKILL.md#笔记输出格式)：
   `sources:` 与 `## 来源` 指向该篇 `raw/articles/`，不指向专辑 manifest；正文至少包含 2 个
   概念 wikilink。
4. 全部成功 query 完成后更新 `index.md`、`log.md` 并刷新 catalog。任何单篇失败须在交付
   摘要中列出 URL 与 gate 原因；不能伪称为全量完成，也不能用空壳 query 占位。

因此，`--limit 10` 表示“摄入并生成最近 10 篇的 query”，而 discovery-only 中它只表示“列出最近
10 篇”。单篇的 raw 和 query 仍遵循既有命名、验证与来源链，不把“未处理其余 50 篇”写入 query。

### Step A1: 远程 URL 抓取

```bash
python <skill-dir>/scripts/extract_article.py "URL" \
  --save-raw --wiki-root /media/yhr/2T/files/wiki
```

自动检测平台（Substack/Medium/X/博客），trafilatura 优先、bs4 回退。
提取正文中的图片到 `raw/articles/images/<slug>/`，过滤 logo/icon/avatar 等噪声。

输出 JSON（含 title/author/date/body/platform/slug/images）。

**成功 gate**：标题非空、正文不是验证码/导航页且内容足以蒸馏；任一项失败，
不得把该结果归档为 raw article。

### Step A1-WeChat fallback：公开微信文章

仅当 `https://mp.weixin.qq.com/...` 的直接抓取未通过标题/正文 gate 时使用。它是
**一次性回退**，不重试、不使用账号/cookie，也不接触非公开文章。

前置条件（由环境管理员一次性安装，不在常规摄入时自动安装）：

```bash
uv tool install wechat-article-to-markdown
uv tool run --from 'camoufox[geoip]' camoufox fetch
```

调用 adapter；`--fallback-reason` 必须记录已经观察到的 direct gate 失败事实：

```bash
python <skill-dir>/scripts/ingest_wechat_article.py "WECHAT_URL" \
  --wiki-root /media/yhr/2T/files/wiki \
  --fallback-reason "direct extraction returned an empty article body"
```

adapter 使用隔离临时目录运行 CLI，验证唯一 Markdown、非空标题和足够正文后，写入：

- `raw/articles/YYYYMMDD-wechat-<url-sha12>.md`
- `raw/articles/images/YYYYMMDD-wechat-<url-sha12>/`（若下载到图片）

它不会覆盖既有 raw capture；同一 URL 已归档时停止并复用现有 raw。adapter 完成的是
**原始归档**，随后仍执行 Step A3；不要把第三方 CLI 的 `output/` 当作 wiki 来源。
若 adapter 不可用或仍未通过 gate，改走 Step A2 的 Clippings/分享文本路径，不再循环回退。

### Step A1-fallback: Jina Reader（Cloudflare 被挡时）

当目标页面被 Cloudflare/反爬保护 → curl + trafilatura 失败或返回空 → 使用 Jina Reader 抓取：

```bash
curl -sL "https://r.jina.ai/<TARGET_URL>" --proxy http://127.0.0.1:7890 --connect-timeout 30 --max-time 60 | python3 -c "
import sys, json
data = sys.stdin.read()
print(data)
" > /tmp/jina_output.md
```

**适用场景**：platform.openai.com、docs.anthropic.com、及其他 Cloudflare 保护的文档页面。
**不适用**：X/Twitter、需要登录的页面、JS 重度渲染的 SPA。

> Jina Reader 需要代理访问（r.jina.ai 在国内网络被阻断）。
> 返回格式为 Markdown，含标题层级、图片链接、表格。质量高于 trafilatura 的纯文本提取。
> 抓取完成后保存为 `raw/articles/<slug>.md`，后续蒸馏流程不变。

### Step A2: Clippings-first 路由

`Clippings/` 是浏览器材料的统一临时收件箱，不是持久存储。对每个 Clipping，先读 YAML
frontmatter 的 `source` / `source_url`、标题、正文和本地附件；先执行 Step 0 的 `--file`
身份检查，**再复制到 `raw/clippings/<file>.md`** 作为永久 provenance snapshot。不要删除原始
Clippings 文件；其清理由独立 closeout gate 决定。

归档后按 `source_url` 和内容完整度路由，不把浏览器剪藏误当作原始媒体或 PDF：

归档完成后、选择下表管线前，复用“统一 subject + intent 判定”。若 clipping 指向软件、仓库、开发工具、平台或产品且意图是系统学习，停止本次 Acquisition，自动将 archive path 与 packet 交给独立 `$chart` 执行；`chart` 必须先独立执行自己的 source identity，不继承 Acquisition owner/state。若只是归档该软件相关的单篇材料，仍按下表继续 Acquisition。无法判断时先询问上述二选一。

| Clipping 中的来源/内容 | 后续管线 |
|------|------|
| YouTube、Bilibili、小红书、X/Twitter 视频或本地音视频 | 继续视频管线：视频/音频/转录留在既有 `raw/assets/`、`raw/transcripts/`；Clipping archive 仅保留浏览器发现和上下文。 |
| PDF URL 或可访问的本地 PDF | 继续 PDF 管线，保留原 PDF 与提取文本至 `raw/papers/`；Clipping archive 不是 PDF 的替代品。 |
| `mp.weixin.qq.com/mp/appmsgalbum` | 继续专辑 discovery；用户要摄入时仍须指定 `--limit N`，不得从 Clipping 的摘要推断批量范围。 |
| 有足够正文的普通文章、登录后页面或动态页 | 以 `raw/clippings/` archive 为正文来源，直接执行 Step A3。不要为了复制一份已捕获正文而重新抓取受限页面。 |
| 只有片段、正文不足，但有普通文章/微信文章 URL | 以 Clipping archive 留底，再走一次 Step A1（微信只在 direct gate 失败后走一次 WeChat fallback）。 |
| 缺少 `source_url` | 仅当归档正文足以蒸馏时走 Step A3；否则停止并报告缺少可路由来源，不猜测 URL 或内容类型。 |

一个 Clipping 若触发专用管线，最终 query 的 `sources:` 和 `## 来源` 必须同时保留
`raw/clippings/` snapshot 与该管线产生的原始 artifact；普通文章 query 只引用其实际采用的
archive。跨入口去重仍以 canonical URL 和内容 hash 为准，不能因 Clipping 已归档跳过 Step 0。

```bash
mkdir -p /media/yhr/2T/files/wiki/raw/clippings
cp "/media/yhr/2T/files/wiki/Clippings/<file>.md" "/media/yhr/2T/files/wiki/raw/clippings/<file>.md"
```

普通文章的笔记 `sources:` 和 `## 来源` 段引用 `raw/clippings/<file>.md`，不引用
`Clippings/`。专用管线的来源链按上表追加其原始 artifact。

### Step A3: 蒸馏 → 结构化笔记（默认）

读取正文，按 [蒸馏规则](../SKILL.md#蒸馏规则) 生成笔记 → `queries/<YYYYMMDD>-<slug>.md`。这是单篇文章、
专辑选中文章及其他成功摄入材料的默认下一步；不要把 query 生成当作额外触发条件。
