#!/usr/bin/env python3
"""Transcribe extracted audio with FunASR and write a wiki transcript."""

from __future__ import annotations

import argparse
import json
import re
import sys
import wave
from datetime import date
from pathlib import Path
from typing import Any


DEFAULT_FUNASR_MODEL = "iic/SenseVoiceSmall"
DEFAULT_VAD_MODEL = "fsmn-vad"


def format_timestamp(seconds: float) -> str:
    milliseconds = int(round((seconds - int(seconds)) * 1000))
    total = int(seconds)
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"
    return f"{minutes:02d}:{secs:02d}.{milliseconds:03d}"


def clean_text(text: str) -> str:
    for marker in (
        "<|zh|>",
        "<|en|>",
        "<|ja|>",
        "<|yue|>",
        "<|ko|>",
        "<|nospeech|>",
        "<|withitn|>",
        "<|woitn|>",
        "<|NEUTRAL|>",
        "<|HAPPY|>",
        "<|SAD|>",
        "<|ANGRY|>",
        "<|Speech|>",
        "<|BGM|>",
        "<|Applause|>",
        "<|Laughter|>",
    ):
        text = text.replace(marker, "")
    text = re.sub(r"<\|[^|]+?\|>", "", text)
    return " ".join(text.split())


def display_path(path: str | Path, root: Path) -> str:
    path_obj = Path(path)
    try:
        return str(path_obj.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def split_text_chunks(text: str) -> list[str]:
    chunks = re.split(r"(?=<\|(?:zh|en|ja|yue|ko|nospeech)\|>)", text)
    if len(chunks) <= 1:
        chunks = re.split(r"(?<=[.!?。！？])\s+", text)
    return [clean_text(chunk) for chunk in chunks if clean_text(chunk)]


def approximate_timestamps(chunks: list[str], audio_duration: float | None) -> list[dict[str, Any]]:
    if not audio_duration or audio_duration <= 0:
        return [{"start": 0.0, "end": 0.0, "text": chunk} for chunk in chunks]

    total_weight = sum(max(len(chunk), 1) for chunk in chunks)
    elapsed = 0.0
    segments: list[dict[str, Any]] = []
    for chunk in chunks:
        weight = max(len(chunk), 1)
        start = elapsed
        elapsed += audio_duration * weight / total_weight
        segments.append({"start": round(start, 3), "end": round(elapsed, 3), "text": chunk})
    return segments


def get_audio_duration(audio_path: Path) -> float | None:
    if audio_path.suffix.lower() != ".wav":
        return None
    try:
        with wave.open(str(audio_path), "rb") as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            return frames / float(rate) if rate else None
    except wave.Error:
        return None


def normalize_segments(result: Any, audio_duration: float | None = None) -> tuple[list[dict[str, Any]], str]:
    items = result if isinstance(result, list) else [result]
    segments: list[dict[str, Any]] = []
    fallback_chunks: list[str] = []

    for item in items:
        if not isinstance(item, dict):
            continue

        sentence_info = item.get("sentence_info")
        if isinstance(sentence_info, list):
            for sentence in sentence_info:
                if not isinstance(sentence, dict):
                    continue
                text = clean_text(str(sentence.get("text", "")))
                if not text:
                    continue
                start = float(sentence.get("start", 0)) / 1000.0
                end = float(sentence.get("end", sentence.get("start", 0))) / 1000.0
                segments.append({"start": start, "end": end, "text": text})

        if segments:
            continue

        fallback_chunks.extend(split_text_chunks(str(item.get("text", ""))))

    if segments:
        return segments, "exact"

    segments = approximate_timestamps(fallback_chunks, audio_duration)
    timestamp_mode = "approximate" if audio_duration and len(segments) > 1 else "none"
    return segments, timestamp_mode


def render_markdown(
    *,
    video_id: str,
    source_url: str,
    platform: str,
    title: str,
    audio_path: str,
    video_path: str,
    raw_json_path: str,
    language: str,
    model: str,
    segments: list[dict[str, Any]],
    timestamp_mode: str,
    confidence: str,
) -> str:
    lines = [
        "---",
        f"source_url: {source_url}",
        f"video_id: {video_id}",
        f"platform: {platform}",
        f"language: {language}",
        f"ingested: {date.today().isoformat()}",
        "asr_engine: funasr",
        f"asr_model: {model}",
        f"timestamp_mode: {timestamp_mode}",
        f"confidence: {confidence}",
        "---",
        "",
        f"# {video_id} 视频转录稿",
        "",
        "## 基本信息",
        f"- **来源**: {platform}",
        f"- **原始链接**: {source_url}",
        f"- **标题**: {title}",
        f"- **视频文件**: {video_path}",
        f"- **音频文件**: {audio_path}",
        f"- **ASR JSON**: {raw_json_path}",
        f"- **转录方式**: FunASR `{model}`",
        f"- **时间戳模式**: {timestamp_mode}",
        f"- **质量标记**: {confidence}",
        "",
        "---",
        "",
        "## 转录正文",
        "",
    ]

    for segment in segments:
        text = clean_text(str(segment.get("text", "")))
        if not text:
            continue
        start = float(segment.get("start", 0.0))
        lines.append(f"[{format_timestamp(start)}] {text}")
        lines.append("")

    # 相关笔记：转录时预填媒体文件 wikilinks，笔记链接留空待补
    lines.append("## 相关笔记")
    lines.append("")
    lines.append("- 结构化笔记：（创建后补填 `[[wikilink]]`）")
    if video_path:
        rel_video = "../" + video_path.split("/", 1)[1] if video_path.startswith("raw/") else video_path
        lines.append(f"- 视频：[[{rel_video}]]")
    if audio_path:
        rel_audio = "../" + audio_path.split("/", 1)[1] if audio_path.startswith("raw/") else audio_path
        lines.append(f"- 音频：[[{rel_audio}]]")
    lines.append(f"- FunASR JSON：`{raw_json_path}`")

    return "\n".join(lines).rstrip() + "\n"


def transcribe_with_funasr(args: argparse.Namespace) -> Any:
    try:
        from funasr import AutoModel
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "FunASR is not installed. Install it with: pip install -U funasr modelscope"
        ) from exc

    model_kwargs: dict[str, Any] = {"model": args.model}
    model_kwargs["disable_update"] = True
    if args.vad_model != "none":
        model_kwargs["vad_model"] = args.vad_model
        model_kwargs["vad_kwargs"] = {"max_single_segment_time": args.max_single_segment_time}
    if args.punc_model != "none":
        model_kwargs["punc_model"] = args.punc_model
    if args.device != "auto":
        model_kwargs["device"] = args.device

    model = AutoModel(**model_kwargs)
    generate_kwargs: dict[str, Any] = {
        "input": str(args.audio),
        "language": args.language,
        "use_itn": True,
        "batch_size_s": args.batch_size_s,
    }
    if args.vad_model != "none":
        generate_kwargs["merge_vad"] = True
        generate_kwargs["merge_length_s"] = args.merge_length_s
    if args.sentence_timestamp and args.punc_model != "none":
        generate_kwargs["sentence_timestamp"] = True
    return model.generate(**generate_kwargs)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe an audio file with FunASR and write raw JSON plus Markdown transcript."
    )
    parser.add_argument("audio", type=Path, help="Audio file to transcribe.")
    parser.add_argument("--wiki-root", type=Path, default=Path.cwd())
    parser.add_argument("--video-id", help="Stable video id. Defaults to audio stem.")
    parser.add_argument("--source-url", default="")
    parser.add_argument("--platform", default="unknown")
    parser.add_argument("--title", default="")
    parser.add_argument("--video-path", default="")
    parser.add_argument("--language", default="auto")
    parser.add_argument("--model", default=DEFAULT_FUNASR_MODEL)
    parser.add_argument("--vad-model", default=DEFAULT_VAD_MODEL)
    parser.add_argument("--punc-model", default="none")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--batch-size-s", type=int, default=60)
    parser.add_argument("--merge-length-s", type=int, default=15)
    parser.add_argument("--max-single-segment-time", type=int, default=30000)
    parser.add_argument("--sentence-timestamp", dest="sentence_timestamp", action="store_true", default=True)
    parser.add_argument("--no-sentence-timestamp", dest="sentence_timestamp", action="store_false")
    parser.add_argument("--confidence", default="medium")
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    args.audio = args.audio.expanduser().resolve()
    if not args.audio.exists():
        print(json.dumps({"ok": False, "error": f"Audio file not found: {args.audio}"}, ensure_ascii=False), file=sys.stderr)
        return 2

    wiki_root = args.wiki_root.expanduser().resolve()
    output_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir
        else wiki_root / "raw" / "transcripts"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    video_id = args.video_id or args.audio.stem
    raw_json_path = output_dir / f"{video_id}.funasr.json"
    transcript_path = output_dir / f"{video_id}_transcript.md"

    try:
        raw_result = transcribe_with_funasr(args)
    except RuntimeError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 127

    raw_json_path.write_text(json.dumps(raw_result, ensure_ascii=False, indent=2), encoding="utf-8")
    segments, timestamp_mode = normalize_segments(raw_result, audio_duration=get_audio_duration(args.audio))
    markdown = render_markdown(
        video_id=video_id,
        source_url=args.source_url,
        platform=args.platform,
        title=args.title,
        audio_path=display_path(args.audio, wiki_root),
        video_path=display_path(args.video_path, wiki_root) if args.video_path else "",
        raw_json_path=display_path(raw_json_path, wiki_root),
        language=args.language,
        model=args.model,
        segments=segments,
        timestamp_mode=timestamp_mode,
        confidence=args.confidence,
    )
    transcript_path.write_text(markdown, encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "asr_engine": "funasr",
                "asr_model": args.model,
                "raw_json": str(raw_json_path),
                "transcript": str(transcript_path),
                "segments": len(segments),
                "timestamp_mode": timestamp_mode,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
