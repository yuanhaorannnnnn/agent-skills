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

## ASR backend

Use FunASR `iic/SenseVoiceSmall` by default for local transcription. It is preferred over Whisper CLI for Chinese social-video audio because it handles Chinese and mixed-language speech more reliably in this workflow.

If `scripts/transcribe_audio.py` reports that FunASR is missing, install:

```bash
pip install -U funasr modelscope
```

The first transcription can download model files. If network access is unavailable, pre-download the model into the local ModelScope cache before running the skill.
