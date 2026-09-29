# Acquisition route: video pipeline

## 视频管线

### Step V0: X/Twitter → YouTube 自动查找

X 视频 CDN（video.twimg.com）对国内网络不稳定。**处理 X/Twitter 链接时，先尝试找 YouTube 对应版本：**

1. 下载元数据：`yt-dlp --dump-json "X_URL" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('description','')[:300]); print(d.get('uploader',''))"`
2. 用描述 + 作者名搜索：`WebSearch "site:youtube.com {uploader} {description key terms}"`
3. 如果命中 YouTube 链接且时长匹配 → **用 YouTube 版下载**，跳过 X 下载
4. 没有命中 → fallback X 下载

### Step V1: 下载

```bash
python <skill-dir>/scripts/ingest_video.py "VIDEO_URL"
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
python <skill-dir>/scripts/transcribe_audio.py raw/assets/audio/<video_id>.wav \
  --video-id <video_id> \
  --source-url "VIDEO_URL" \
  --platform <youtube|x|bilibili|xiaohongshu>
```

默认模型 `iic/SenseVoiceSmall`，输出：
- FunASR JSON：`raw/transcripts/<video_id>.funasr.json`
- 转录稿：`raw/transcripts/<video_id>_transcript.md`

时间戳模式默认 `approximate`（SenseVoiceSmall 不支持逐字时间戳）。

### Step V4: 蒸馏 → 结构化笔记

读取转录稿，按 [蒸馏规则](../SKILL.md#蒸馏规则) 生成笔记 → `queries/<YYYYMMDD>-<slug>.md`。
