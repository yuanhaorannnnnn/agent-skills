---
name: Acquisition
description: |
  Load when the user shares a video or article URL and wants to save it into the
  wiki, or says "把这篇/这个视频消化一下", "提取干货", "整理要点", "ingest this",
  "summarize into the wiki". Handles X/YouTube/Bilibili/Xiaohongshu videos and
  article URLs (Substack, Medium, blog posts), PDF files, or local Clippings files.
version: "3.0.0"
user_invocable: true
---

# Content Ingest: 统一内容摄入 + 知识蒸馏

将视频、文章摄入到 wiki，去噪、蒸馏、生成结构化笔记。

## 自动路由

根据输入自动选择管线：

```
输入
  ├─ x.com / twitter.com → 自动查找 YouTube 对应版
  │     └─ 命中 → YouTube 管线 | 未命中 → X 下载
  │
  ├─ youtube.com / bilibili.com / xhslink.com → 视频管线
  │     下载(yt-dlp) → 音频提取 → FunASR 转录 → 蒸馏 → queries/
  │
  ├─ 普通网页 URL (substack/medium/博客等) → 文章管线
  │     抓取(trafilatura) → 图片提取 → 蒸馏 → queries/
  │
  ├─ PDF URL / 本地 .pdf → PDF 管线
  │     下载/读取 → pymupdf 提取文本 → 保存 raw/papers/ → 蒸馏 → queries/
  │
  ├─ 本地 .md / Clippings/*.md → 直接读文件 → 归档 raw/clippings/ → 蒸馏 → queries/
  │
  └─ 本地 .mp4 / .wav → 音频提取 → FunASR 转录 → 蒸馏 → queries/
```

**客户端自动路由**：`ingest_content.py` 自动检测输入类型并路由。

## 视频管线

### Step V0: X/Twitter → YouTube 自动查找

X 视频 CDN（video.twimg.com）对国内网络不稳定。**处理 X/Twitter 链接时，先尝试找 YouTube 对应版本：**

1. 下载元数据：`yt-dlp --dump-json "X_URL" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('description','')[:300]); print(d.get('uploader',''))"`
2. 用描述 + 作者名搜索：`WebSearch "site:youtube.com {uploader} {description key terms}"`
3. 如果命中 YouTube 链接且时长匹配 → **用 YouTube 版下载**，跳过 X 下载
4. 没有命中 → fallback X 下载

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

**处理前先归档。** Clippings/ 是 Obsidian Clipper 的临时收件箱，不是持久存储。

1. 读取 `Clippings/<file>.md`，从 YAML frontmatter 获取 title/source/author/date
2. **复制到 `raw/clippings/<file>.md`** —— 永久归档
3. 后续蒸馏基于归档副本，原始 Clippings 文件在处理完成后可删除

```bash
mkdir -p /media/yhr/2T/files/wiki/raw/clippings
cp "/media/yhr/2T/files/wiki/Clippings/<file>.md" "/media/yhr/2T/files/wiki/raw/clippings/<file>.md"
```

笔记的 `sources:` 和 `## 来源` 段引用 `raw/clippings/<file>.md`，不引用 `Clippings/`。

### Step A3: 蒸馏 → 结构化笔记

读取正文，按 [蒸馏规则](#蒸馏规则) 生成笔记 → `queries/<slug>.md`。

## PDF 管线

### Step P1: 获取 PDF

**远程 URL**：curl 下载
```bash
curl -sL "PDF_URL" -o /media/yhr/2T/files/wiki/raw/papers/<slug>.pdf --connect-timeout 15
```

**本地文件**：直接使用已有路径。

### Step P2: 提取文本

```bash
python3 -c "
import fitz
doc = fitz.open('/media/yhr/2T/files/wiki/raw/papers/<slug>.pdf')
for page in doc:
    print(page.get_text())
" > /media/yhr/2T/files/wiki/raw/papers/<slug>.txt
```

依赖 `pymupdf`（`pip install pymupdf`）。

### Step P3: 蒸馏 → 结构化笔记

读取 `raw/papers/<slug>.txt`，按 [蒸馏规则](#蒸馏规则) 生成笔记 → `queries/<slug>.md`。

PDF 通常篇幅较长（10-50 页），蒸馏时注意：
- 先通读全文提取核心论点框架，再填充细节
- 保留原文的关键数据/表格/数字
- 示例代码完整保留

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
tags: [{video|article}, {平台}, {领域标签}]   # 所有 tag 用复数
sources: [{raw/transcripts/xxx.md 或 raw/articles/xxx.md 或 raw/clippings/xxx.md 或 raw/papers/xxx.pdf}]
source_url: {原始URL}
confidence: medium
rating: {1-7}                             # 个人评分：7=改变人生，1=负面
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

**两个层次的 wikilink：**

### 1. 来源链（必须）
笔记底部 `## 来源` 段链接原始文件：

```markdown
## 来源
- 视频：[[raw/assets/video/<video_id>/<video_id>.mp4]]
- 音频：[[raw/assets/audio/<video_id>.wav]]
- 转录稿：[[raw/transcripts/<video_id>_transcript.md]]
```

### 2. 概念引用（必须 — 每篇至少 2 个）
笔记正文中首次提及的关键概念、方法、工具，用 `[[wikilinks]]` 链接到已有 wiki 页面（concepts/ 或相关 queries/）。检查 `index.md` 找到相关页面。

```markdown
这套系统的核心是 [[3d-gaussian-splatting]] 管线，类似于 [[raycast-v2-technical-deep-dive|Raycast 的 hybrid 架构]] 中的 IPC 设计。
```

如果目标页面尚不存在但值得创建 → 依然加 `[[wikilink]]`（unresolved link），作为"间接意图设定"。

转录稿底部 `## 相关笔记` 段链接回笔记和媒体文件。

## 索引更新

完成笔记后更新 `index.md` 和 `log.md`：

```markdown
## [YYYY-MM-DD] create | {标题} → queries/{slug}.md
```

## 原始材料归档

**所有输入类型在 raw/ 目录下都有留底。** 全输入覆盖：

| 输入 | 留底位置 |
|------|---------|
| YouTube/Bilibili/X 视频 | `raw/assets/video/` + `raw/transcripts/` |
| 网页文章 | `raw/articles/` |
| Clippings（浏览器剪藏） | `raw/clippings/`（处理前先复制归档） |
| 本地 mp4/wav | `raw/transcripts/` |
| PDF（远程/本地） | `raw/papers/` |
| HTML 电子书 | `raw/books/` |

raw/ 是图书馆——永久留存，不因是否写了笔记而增删。query/ 是读后感。图书馆里没读完的书很正常。

笔记的 `sources:` 和 `## 来源` 段引用 raw/ 下的归档路径（如 `raw/clippings/<file>.md` 或 `raw/papers/<slug>.pdf`），再用 `source_url: '@source_url'` 指向原始 URL 出处。

## 依赖

- Python 3.9+, yt-dlp, ffmpeg
- `funasr`, `modelscope`（视频转录）
- `trafilatura`, `beautifulsoup4`（文章提取）
- `pymupdf`（PDF 文本提取）

## 资源

- `scripts/ingest_video.py`：yt-dlp 视频下载
- `scripts/transcribe_audio.py`：FunASR 转录
- `scripts/extract_article.py`：文章正文提取 + 图片下载
- `references/download-notes.md`：平台注意事项和排错
