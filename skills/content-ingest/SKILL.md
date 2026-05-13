---
name: content-ingest
description: |
  Load when the user shares a video or article URL and wants to save it into the
  wiki, or says "把这篇/这个视频消化一下", "提取干货", "整理要点", "ingest this",
  "summarize into the wiki". Handles X/YouTube/Bilibili/Xiaohongshu videos and
  article URLs (Substack, Medium, blog posts) or local Clippings files.
version: "2.0.0"
user_invocable: true
---

# Content Ingest: 统一内容摄入 + 知识蒸馏

将视频、文章摄入到 wiki，去噪、蒸馏、生成结构化笔记。

## Step 0: 查重

处理前先检查 `raw/PROCESSED.md`，避免重复摄入：

```bash
grep -F "SOURCE_URL_OR_PATH" raw/PROCESSED.md
```

如果命中，说明该来源已处理过，告知用户对应的输出页面并确认是否需要重新摄入。

## 自动路由

根据输入自动选择管线：

```
输入
  ├─ 用户意图："下载/离线/镜像" → 静态站点镜像
  │     wget 整站下载 → 链接本地化 → 生成资源列表笔记 → queries/
  │
  ├─ youtube.com / x.com / bilibili.com / xhslink.com → 视频管线
  │     下载(yt-dlp) → 音频提取 → FunASR 转录 → 蒸馏 → queries/
  │
  ├─ 普通网页 URL (substack/medium/博客等) → 文章管线
  │     抓取(trafilatura) → 图片提取 → 蒸馏 → queries/
  │
  ├─ 本地 .md / Clippings/*.md → 直接读文件 → 蒸馏 → queries/
  │
  └─ 本地 .mp4 / .wav → 音频提取 → FunASR 转录 → 蒸馏 → queries/
```

**客户端自动路由**：`ingest_content.py` 自动检测输入类型并路由。

## 视频管线

### Step V1: 下载

```bash
python ~/.agents/skills/content-ingest/scripts/ingest_video.py "VIDEO_URL"
```

选项：
- `--dry-run`：预览 yt-dlp 命令，不实际下载
- `--cookies-from-browser chrome`：需要认证的 X/小红书 视频
- `--proxy http://127.0.0.1:7890`：YouTube 代理
- `--playlist`：下载播放列表

支持平台：YouTube、X/Twitter、Bilibili、小红书（通过 yt-dlp 提取器）。

输出目录：`raw/assets/video/<video_id>/`

### Step V2: 提取音频

```bash
ffmpeg -i raw/assets/video/<video_id>/<video_id>.mp4 -vn -ar 16000 -ac 1 raw/assets/audio/<video_id>.wav
```

### Step V3: FunASR 转录

```bash
python ~/.agents/skills/content-ingest/scripts/transcribe_audio.py raw/assets/audio/<video_id>.wav \
  --video-id <video_id> \
  --source-url "VIDEO_URL" \
  --platform <youtube|x|bilibili|xiaohongshu>
```

默认模型 `iic/SenseVoiceSmall`，输出：
- FunASR JSON：`raw/transcripts/<video_id>.funasr.json`
- 转录稿：`raw/transcripts/<video_id>_transcript.md`

时间戳模式默认 `approximate`（SenseVoiceSmall 不支持逐字时间戳）。

### Step V4: 蒸馏 → 结构化笔记

读取转录稿，按 [蒸馏规则](#蒸馏规则) 生成笔记 → `queries/<slug>.md`。

## 文章管线

### Step A1: 远程 URL 抓取

```bash
python ~/.agents/skills/content-ingest/scripts/extract_article.py "URL" \
  --save-raw --wiki-root /media/yhr/2T/files/wiki
```

自动检测平台（Substack/Medium/X/博客），trafilatura 优先、bs4 回退。
提取正文中的图片到 `raw/articles/images/<slug>/`，过滤 logo/icon/avatar 等噪声。

输出 JSON（含 title/author/date/body/platform/slug/images）。

### Step A2: 本地 Clippings

跳过抓取。直接读取 `Clippings/*.md`，从 YAML frontmatter 获取 title/source/author/date。

### Step A3: 蒸馏 → 结构化笔记

读取正文，按 [蒸馏规则](#蒸馏规则) 生成笔记 → `queries/<slug>.md`。

## 静态站点镜像

当用户分享的是一个**交互式演示站、HTML 文档站、教程站**（不适合文本提取），且用户意图是"下载下来离线看"而非"提取干货"时，用 wget 整站镜像：

```bash
wget --mirror --page-requisites --adjust-extension --convert-links --no-parent \
  -e http_proxy=http://127.0.0.1:7890 -e https_proxy=http://127.0.0.1:7890 \
  --directory-prefix=/media/yhr/2T/files/wiki/raw/assets \
  "URL"
```

下载完成后生成 query 笔记：列出所有页面文件名和用途，记录离线打开方式（`xdg-open raw/assets/<host>/<path>/index.html`）。标准索引更新（index.md + log.md + PROCESSED.md）同上。

**和文章管线的区别**：文章管线提取文本，蒸馏可操作知识。镜像管线保留完整的 HTML/CSS/JS，在浏览器里体验。

## 蒸馏规则

从内容中提取**可操作**的知识。核心原则：找"how"不找"what"。

**提取（按优先级）：**

1. 具体操作步骤 — 分几步？每步用什么工具/命令/配置？
2. 参数/配置/数字 — 调了什么参数？什么值？为什么？
3. 决策规则 — 什么条件选什么方案？判断依据？
4. 失败/踩坑记录 — 试过什么但失败了？为什么？
5. 反直觉发现 — 什么不符合直觉但有效的规律？

**跳过：**

- 个人故事、职业背景
- 行业趋势展望
- 泛泛推荐（无具体 why/how）
- 纯观点/态度（无论证和数据）
- 无法迁移的一次性经验

## 笔记输出格式

```markdown
---
title: "{一句话总结}"
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
type: query
tags: [{video|article}, {平台}, {领域标签}]
sources: [{raw/transcripts/xxx.md 或 raw/articles/xxx.md 或 Clippings/xxx.md}]
source_url: {原始URL}
confidence: medium
---

# {标题}

## 核心观点

{1-3 句话核心论点及为什么值得关注}

## 关键要点

1. **{要点标题}**
   {具体说明，含数字/命令/配置/判断条件}
2. ...

## 行动建议

{3-5 条可立即执行的祈使句}
```

## Wikilink 规范

笔记底部 `## 来源` 段用 `[[wikilinks]]` 链接原始文件：

```markdown
## 来源
- 视频：[[raw/assets/video/<video_id>/<video_id>.mp4]]
- 音频：[[raw/assets/audio/<video_id>.wav]]
- 转录稿：[[raw/transcripts/<video_id>_transcript.md]]
```

转录稿底部 `## 相关笔记` 段链接回笔记和媒体文件。
**Wikilink 只用于来源链**，正文禁止引用不存在的概念/实体页面。

## 索引更新

完成笔记后，更新三处索引：

1. **`index.md`** — 在对应区域追加一行
2. **`log.md`** — 追加时序记录：
   ```markdown
   ## [YYYY-MM-DD] create | {标题} → queries/{slug}.md
   ```
3. **`raw/PROCESSED.md`** — 追加已处理标记，防止未来重复摄入：
   ```markdown
   | YYYY-MM-DD | video/article | raw/transcripts/xxx.md 或 Clippings/xxx.md | queries/{slug}.md |
   ```

## 依赖

- Python 3.9+, yt-dlp, ffmpeg
- `funasr`, `modelscope`（视频转录）
- `trafilatura`, `beautifulsoup4`（文章提取）

## 资源

- `scripts/ingest_video.py`：yt-dlp 视频下载
- `scripts/transcribe_audio.py`：FunASR 转录
- `scripts/extract_article.py`：文章正文提取 + 图片下载
- `references/download-notes.md`：平台注意事项和排错
