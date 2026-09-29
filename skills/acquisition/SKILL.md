---
name: acquisition
description: |
  Load when the user shares a video or article URL and wants to save it into the
  wiki, or says "把这篇/这个视频消化一下", "提取干货", "整理要点", "ingest this",
  "summarize into the wiki". Handles X/YouTube/Bilibili/Xiaohongshu videos and
  article URLs (including public WeChat Official Account links and albums), PDF
  files, or local Clippings files.
metadata:
  version: "3.5.0"
---

# Content Ingest: 统一内容摄入 + 知识蒸馏

将视频、文章摄入到 wiki，去噪、蒸馏、生成结构化笔记。默认交付是“原始归档 + query”；
只有用户明确要求 raw-only 时才跳过 query。

## Step 0：跨入口身份检查

路由、下载或复制 raw 之前，先对每个独立来源执行：

```bash
python <skill-dir>/scripts/source_identity.py \
  --wiki-root /media/yhr/2T/files/wiki --url "SOURCE_URL"

python <skill-dir>/scripts/source_identity.py \
  --wiki-root /media/yhr/2T/files/wiki --file "Clippings/FILE.md"
```

脚本统一比较 `canonical_url` 和正文 `content_sha256`，覆盖手机书签、PC clipping、
直接 URL、X bookmark 等不同入口。URL 规范化只移除 fragment、常见追踪参数和 viewer noise；
保留用于识别内容的参数。

- 命中已有完整 raw + query：复用现有产物，报告 `skipped`，不得再次归档或生成 query。
- 只命中 raw：复用 raw，继续生成缺失 query。
- 只命中 query 或来源链不完整：检查其 `sources:`，补齐缺失环节，不复制完整产物。
- 同 URL 但正文变化：保留已有 raw，使用可追溯的新文件名归档新版本，并在结果中标明更新。
- URL 不可用且无本地正文：无法做可靠身份判断；继续管线，但明确这是弱去重。

## 自动路由

### 统一 subject + intent 判定

在直接输入进入下表路由前，先判断“用户要学什么”而不是只看输入格式：

- subject 属于 repository、software、developer tool、platform 或 product，且 intent 是系统学习（架构、源码、版本、运行、诊断、二开、维护或学习路线）→ **停止 Acquisition 内容管线**，自动启动独立 `$chart` 执行。handoff packet 必须携带 `subject`、`intent`、`source_url/path`、`origin`、`clipping archive path if created`、`raw/query status`；这是 ownership transfer，不是 `calls`。
- 资料、书、PDF、文章、视频等内容本身是学习对象 → 继续 Acquisition；软件相关的单篇材料若用户只要求归档/摘要，也继续 Acquisition。
- subject 或 intent 不清 → 询问二选一：“按内容归档并蒸馏（`acquisition`），还是按软件/产品建立 Study Hub（`$chart`）？”在答案明确前不启动任何管线。

同一判定适用于直接 URL、本地文件和 Clippings。Clippings 必须先完成 identity/archive，再 classifier；命中软件系统学习后携带 packet handoff。直接输入先分类再 handoff，不创建 acquisition raw/query，由 `chart` 自行处理。

根据输入自动选择管线：

```
输入
  ├─ x.com / twitter.com → 自动查找 YouTube 对应版
  │     └─ 命中 → YouTube 管线 | 未命中 → X 下载
  │
  ├─ youtube.com / bilibili.com / xhslink.com → 视频管线
  │     下载(yt-dlp) → 音频提取 → FunASR 转录 → 蒸馏 → queries/
  │
  ├─ mp.weixin.qq.com/mp/appmsgalbum → 专辑管线
  │     滚动发现 → 规范化/去重 → 选择 N 篇 → 单篇 raw → 每篇 query → index/log/catalog
  │
  ├─ mp.weixin.qq.com/s → 文章管线（默认交付 raw + query）
  │     直接抓取 → 标题/正文 gate 失败 → WeChat CLI 回退 → 蒸馏 → query
  │
  ├─ 普通网页 URL (substack/medium/博客等) → 文章管线
  │     抓取(trafilatura) → Cloudflare 被挡 → Jina Reader 回退 → 蒸馏 → queries/
  │
  ├─ PDF URL / 本地 .pdf → PDF 管线
  │     下载/读取 → pymupdf 提取文本 → 保存 raw/papers/ → 蒸馏 → queries/
  │
  ├─ Clippings/*.md → Clippings-first 路由（见 Step A2）
  ├─ 其他本地 .md → 直接读文件 → 归档 raw/clippings/ → 蒸馏 → queries/
  │
  └─ 本地 .mp4 / .wav → 音频提取 → FunASR 转录 → 蒸馏 → queries/
```

**路由方式**：agent 按上表识别输入类型并调用对应脚本；当前没有单一
`ingest_content.py` 入口，不得引用不存在的 router。

## 按输入类型读取管线

完成 Step 0 和自动路由后，只读取命中的一份管线文件：

- X、YouTube、Bilibili、小红书或本地音视频 → [视频管线](references/video-pipeline.md)。
- 普通网页、微信文章/专辑、Clippings 或本地 Markdown → [文章与剪藏管线](references/article-pipeline.md)。
- PDF URL 或本地 PDF → [PDF 管线](references/pdf-pipeline.md)。

每条管线完成 raw 归档后，返回本文件的蒸馏、query 来源链和索引门禁。未命中的分支无需加载。

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

### 先保真，再成文

生成 query 前先完成 evidence pass。不要在读取每个来源后立即写一段连贯摘要；这会在跨来源综合之前丢失数字、限定条件和相互冲突的细节。

在内部按原子信息记录：

```text
claim | evidence ref/位置 | evidence type | 条件或不确定性
```

- `claim` 只表达一个可独立检查的事实、数据、机制、作者判断或失败记录。
- `evidence ref/位置` 指向 raw 文件及可定位的章节、页码、时间戳、图表或原文片段。
- `evidence type` 区分原文陈述、source-reported 结果、本机观察、推断和个人判断。
- 精确保留数字、单位、标识符、版本、样本范围和否定条件；相互冲突的信息分别记录，不先行调和。

完成 evidence pass 后再按读者任务和信息关系组织 prose。该原子记录默认是内部工作状态，不要求额外生成永久文件；来源多、材料长或用户要求审计时，再把它保存为显式 evidence ledger。

## Query 写作门禁

生成或实质重写 query 时，默认加载 `paperwork`，在写入前按其失效机制完成一次清理。该步骤属于 Acquisition 的默认 query 管线；用户不需要额外触发。只生成 raw archive 时跳过。

把 query 视为面向未来自己的技术说明或评价，而不是对原材料的形式化摘要：

1. 先确定文档对象、核心主张、证据层级和主要信息关系，再选择结构；下方“笔记输出格式”是最低字段契约，不要求机械补齐同名章节。
2. 对照 evidence pass 保留关键事实、标识符、数值、适用条件、不确定性以及用户在 `## 阅读讨论` 中提出的问题；不得为了流畅或缩短文字损失这些内容。
3. 删除元叙事、语义重复、模板补全、抽象评价、预防性辩护、错位教学和表演性文风；把机制、证据与边界放在对应结论附近。
4. 区分原文主张、source-reported 结果、本机验证、推断和个人判断；不能把其中一类改写成另一类。
5. 重写后执行双向检查：从正文回到来源，确认主张有证据；从 evidence pass 回到正文，确认关键原子信息没有在摘要和重组中消失。删除任一句话，如果不改变理解、判断、证据强度或后续行动，则继续删除或合并。

`paperwork` 只负责组织与表达，不替代本 skill 的 raw 来源链、frontmatter、wikilink、index/log 和 catalog 门禁。

## 笔记输出格式

文件名固定为 `queries/YYYYMMDD-<english-slug>.md`：

- `YYYYMMDD` 取 query 的 `created` 日期，即摄入/蒸馏日期。
- 文件名前缀必须与 `created` 去除连字符后的值一致。
- 原文发布日期单独保存在 raw frontmatter 的 `published` 或 `date`，不用于 query 文件名。
- `<english-slug>` 仅使用小写字母、数字和连字符。

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
## [YYYY-MM-DD] create | {标题} → queries/{YYYYMMDD}-{slug}.md
```

完成前验证：

1. query basename 匹配 `^[0-9]{8}-[a-z0-9][a-z0-9-]*\.md$`
2. basename 日期前缀等于 frontmatter `created` 去除连字符后的值
3. `sources:` 和 `## 来源` 只引用 `raw/` 归档，不引用 `Clippings/`
4. `index.md`、`log.md` 和相关 wikilinks 使用最终文件名

完成上述写入后刷新 vault catalog：

```bash
python3 /media/yhr/2T/files/wiki/.scripts/build_collection_catalog.py \
  --vault /media/yhr/2T/files/wiki
```

catalog 刷新失败不回滚已完成的摄入；明确报告失败，并保留 query/raw/index/log 作为已完成产物。不得静默留下 stale catalog。

## 原始材料归档

**所有输入类型在 raw/ 目录下都有留底。** 全输入覆盖：

| 输入 | 留底位置 |
|------|---------|
| YouTube/Bilibili/X 视频 | `raw/assets/video/` + `raw/transcripts/` |
| 网页文章 | `raw/articles/` |
| 网页文章（Cloudflare 被挡，Jina Reader 抓取） | `raw/articles/` |
| 微信专辑 URL 清单 | `raw/collections/`（显式 `--save-manifest`） |
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
- `scripts/discover_wechat_album.py`：微信专辑 article URL 发现 + 去重
- `scripts/source_identity.py`：跨入口 canonical URL + content hash 身份检查
- `references/download-notes.md`：平台注意事项和排错

## Canon 输出边界

读取共享契约：`/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md`。

- 旧内容 wiki `/media/yhr/2T/files/wiki` 仍是文章、视频、PDF、剪藏的内容库和 raw archive；不要把这些 raw assets 复制到 Canon。
- 当摄入内容影响本地项目、流程、决策、事故或可复用模式时，创建 `/media/yhr/2T/Canon/raw/update-cards/<date>-acquisition-<slug>.md`，把 wiki 笔记和 raw 路径作为 artifact refs。
- Canon 只保存跨项目长期结论、关联和 artifact refs；`queries/`、`raw/`、`concepts/` 继续由旧内容 wiki 管理。
