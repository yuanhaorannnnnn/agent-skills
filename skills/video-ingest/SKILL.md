---
name: video-ingest
description: |
  Ingest online videos into a wiki source layout. Use when the user wants to
  download videos from X/Twitter, Xiaohongshu, Bilibili, or YouTube, save video
  assets and metadata, prepare subtitle/transcript-ready source files, or
  optionally continue from a downloaded video toward transcript and
  structured-note workflows.
---

# Video Ingest

Use this skill to bring an online video into a local wiki source tree, then transcribe it locally. Downloads use `yt-dlp`; ASR defaults to FunASR `iic/SenseVoiceSmall`.

## Quick Start

From the wiki root, run:

```bash
python ~/.agents/skills/video-ingest/scripts/ingest_video.py "VIDEO_URL"
```

By default, outputs are written under:

```text
raw/assets/video/
```

Use `--dry-run` before network downloads when you need to inspect the planned `yt-dlp` command:

```bash
python ~/.agents/skills/video-ingest/scripts/ingest_video.py "VIDEO_URL" --dry-run
```

Reserve a structured-note mode for the surrounding workflow:

```bash
python ~/.agents/skills/video-ingest/scripts/ingest_video.py "VIDEO_URL" --note none
```

After audio exists, transcribe with FunASR:

```bash
python ~/.agents/skills/video-ingest/scripts/transcribe_audio.py raw/assets/audio/VIDEO_ID.wav --video-id VIDEO_ID
```

For SenseVoiceSmall, timestamps may be approximate because the model can return
punctuated text chunks without exact word timestamps. The transcript frontmatter
records this as `timestamp_mode: approximate`.

## Supported Sources

The downloader supports the platforms through `yt-dlp` extractors:

- X / Twitter: `x.com`, `twitter.com`
- Xiaohongshu: `xiaohongshu.com`, `xhslink.com`
- Bilibili: `bilibili.com`, `b23.tv`
- YouTube: `youtube.com`, `youtu.be`

For X and Xiaohongshu, authentication is often required. If a download fails because the content is private, rate-limited, or login-gated, rerun with cookies:

```bash
python ~/.agents/skills/video-ingest/scripts/ingest_video.py "VIDEO_URL" --cookies-from-browser chrome
```

or:

```bash
python ~/.agents/skills/video-ingest/scripts/ingest_video.py "VIDEO_URL" --cookies cookies.txt
```

## Download Contract

The script:

1. Detects the source platform from the URL.
2. Verifies that `yt-dlp` is installed.
3. Creates the output directory if needed.
4. Downloads one video by default, not whole playlists.
5. Writes the video, info JSON, thumbnail, and available subtitles next to each other.
6. Prints a JSON summary containing the platform, wiki root, output directory, and command.

Default `yt-dlp` behavior:

```text
--write-info-json
--write-thumbnail
--write-subs
--write-auto-subs
--sub-langs zh-Hans,zh,en.*
--merge-output-format mp4
--no-playlist
```

Use `--playlist` only when the user explicitly asks to download a playlist or collection.

## Wiki Workflow

When used in this wiki layout:

1. Download source media into `raw/assets/video/`.
2. Keep files for the same video together under `raw/assets/video/<video_id>/` when creating or reorganizing downloads.
3. If subtitles are downloaded, convert them into `raw/transcripts/<video_id>_transcript.md`.
4. If no subtitles are available, extract audio to `raw/assets/audio/<video_id>.wav`.
5. Run FunASR with `scripts/transcribe_audio.py`.
6. Generate structured notes only when the user asks for them or passes a note option in the surrounding workflow.

Do not claim that a transcript was created unless a transcript file actually exists.

## Local ASR

Use FunASR as the default local ASR backend:

```bash
python ~/.agents/skills/video-ingest/scripts/transcribe_audio.py raw/assets/audio/VIDEO_ID.wav \
  --video-id VIDEO_ID \
  --source-url "VIDEO_URL" \
  --platform x \
  --video-path raw/assets/video/VIDEO_ID/VIDEO_ID.mp4
```

Default model:

```text
iic/SenseVoiceSmall
```

If FunASR is missing, install:

```bash
pip install -U funasr modelscope
```

The first run may download the selected model. Prefer FunASR/SenseVoice for Chinese, dialect, mixed-language, and noisy social-video content. Use Whisper only as a fallback.

## Structured Notes

Structured note generation is a separate optional phase. Treat the note mode as:

```text
none | summary | concept | comparison | query | auto
```

The download script accepts `--note`, but version 1 only records the requested mode in its JSON summary. Default to `none` unless the user explicitly asks for notes, summaries, wiki pages, or structured output. When note generation is requested, the note must include:

- 核心观点
- 关键要点
- 行动建议
- 来源路径（使用 `[[wikilinks]]`，见下方 Wikilink Convention）

For wiki notes, update `index.md` and append `log.md`.

### Wikilink Convention

Ensure Obsidian graph view can trace the full raw → transcript → note chain:

**笔记底部 `## 来源` 段（必须）：**
```markdown
## 来源

- 视频：[[raw/assets/video/<video_id>/<video_id>.mp4]]
- 音频：[[raw/assets/audio/<video_id>.wav]]
- 转录稿：[[raw/transcripts/<video_id>_transcript.md]]
```

**转录稿底部 `## 相关笔记` 段（必须）：**
```markdown
## 相关笔记

- 结构化笔记：[[../queries/<note-slug>.md]]
- 视频：[[../assets/video/<video_id>/<video_id>.mp4]]
- 音频：[[../assets/audio/<video_id>.wav]]
```

转录稿的 `transcribe_audio.py` 脚本会自动生成媒体文件 wikilinks 和占位符，笔记链接需在笔记创建后回填。

**Wikilink 使用规则（必须遵守）：**

1. `[[wikilinks]]` 只允许用于 **来源链**：笔记 ↔ 转录稿 ↔ 媒体文件。这些目标文件确实存在于仓库中。
2. **正文中禁止使用 `[[wikilinks]]` 引用没有对应页面的概念/实体/工具名。** 即如果 `concepts/`、`entities/` 等目录下不存在对应 `.md` 文件，就不能用 `[[]]` 包裹。这类引用直接写纯文本即可。
3. `## 相关链接` 段同样只列出有对应页面的 wikilinks，不列空目标。

## Resources

- `scripts/ingest_video.py`: download online videos and source metadata with `yt-dlp`.
- `scripts/transcribe_audio.py`: transcribe extracted audio with FunASR and write wiki Markdown.
- `references/download-notes.md`: platform notes and troubleshooting guidance.
