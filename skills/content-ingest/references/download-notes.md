# Video Download Notes

## Platform behavior

- YouTube usually works without cookies for public videos, but subtitles vary by creator and locale.
- Bilibili public videos usually work without cookies; higher quality, private, age-restricted, or region-limited content may require cookies.
- X/Twitter often requires cookies because many videos are login-gated or rate-limited.
- Xiaohongshu often requires cookies and may require a browser-like User-Agent or Referer.

## Cookie guidance

Prefer `--cookies-from-browser chrome` or `--cookies-from-browser firefox` when the user has already logged into the target platform in that browser.

Use `--cookies cookies.txt` when the user exports cookies manually. Do not print cookie contents in the final response.

## Troubleshooting

If extraction fails:

1. Re-run with `--dry-run` and inspect the generated command.
2. Try cookies from a logged-in browser.
3. Try a custom User-Agent for Xiaohongshu.
4. Ask the user to confirm the video is accessible in their browser.
5. If the site extractor is broken, update `yt-dlp` before changing this skill.

### Bilibili: yt-dlp HTTP 412 fallback

Bilibili blocks yt-dlp aggressively. If `ingest_video.py` fails with HTTP 412, use the Bilibili playurl API directly:

```bash
# Get CID and metadata
curl -s "https://api.bilibili.com/x/web-interface/view?bvid=BVID" | python3 -c "
import sys, json
d = json.load(sys.stdin)['data']
print(f'cid={d[\"cid\"]}')
print(f'title={d[\"title\"]}')
"

# Get audio stream
curl -s "https://api.bilibili.com/x/player/playurl?bvid=BVID&cid=CID&qn=80&fnver=0&fnval=16&fourk=1" \
  -H "Referer: https://www.bilibili.com" \
  | python3 -c "import sys,json; print(max(json.load(sys.stdin)['data']['dash']['audio'], key=lambda x: x['bandwidth'])['base_url'])"

# Download audio and convert
curl -o audio.m4s -H "Referer: https://www.bilibili.com" "AUDIO_URL"
ffmpeg -y -i audio.m4s -vn -ar 16000 -ac 1 <video_id>.wav
rm audio.m4s
```

## ASR backend

Use FunASR `iic/SenseVoiceSmall` as the primary ASR backend for Chinese social-video audio.

If `scripts/transcribe_audio.py` reports that FunASR is missing, install:

```bash
pip install -U funasr modelscope
```

The first transcription can download model files. If network access is unavailable, pre-download the model into the local ModelScope cache before running the skill.
