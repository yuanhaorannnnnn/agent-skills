#!/usr/bin/env python3
"""Extract filtered conversation turns from Codex / Pi / Claude Code JSONL sessions.

Usage:
  python extract_handoff.py --former codex --cwd /path/to/project
  python extract_handoff.py --former pi    --dir /path/to/project --focus "bug repair"
  python extract_handoff.py --former claude --file /path/to/session.jsonl

Output: JSON with session metadata, token estimate, filtered turns, and candidate info.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path


def slugify_claude(cwd: str) -> str:
    """Claude Code cwd encoding: / → -, _ → -, leading - preserved."""
    return cwd.replace("/", "-").replace("_", "-")


def slugify_pi(cwd: str) -> str:
    """Pi cwd encoding: wrap with --, inner / replaced with -."""
    inner = cwd.strip("/").replace("/", "-")
    return "--" + inner + "--"


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for CJK, ~4 for English."""
    return max(1, len(text) // 3)


def _focus_terms(focus: str | None) -> list[str]:
    if not focus:
        return []
    return [t.lower() for t in re.split(r"\s+", focus.strip()) if t.strip()]


def focus_score(path: Path, focus: str | None) -> int:
    """Return a focus score for a session file via streaming full-file scan.

    Reads the entire file in chunks to avoid missing focus terms in the
    middle of long sessions. This is intentionally scalar — the file must
    be read eventually for extraction, so the marginal cost is low.
    """
    terms = _focus_terms(focus)
    if not terms:
        return 0
    score = 0
    try:
        with open(path, "rb") as f:
            chunk = f.read(1_000_000)
            while chunk:
                data = chunk.decode("utf-8", errors="ignore").lower()
                for term in terms:
                    score += data.count(term) * max(1, len(term))
                chunk = f.read(1_000_000)
    except Exception:
        return 0
    return score


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0


def looks_like_raw_context_dump(text: str) -> bool:
    """Detect injected rules/metadata dumps that are not real user turns."""
    head = text[:2000]
    if head.startswith("# AGENTS.md instructions for"):
        return True
    if "<INSTRUCTIONS>" in head or "</INSTRUCTIONS>" in head:
        return True
    if "<goal_context>" in head and "Continue working toward the active thread goal" in head:
        return True
    if len(text) > 20000 and "# Global Agent Guidance" in head:
        return True
    return False


# ── Codex ──────────────────────────────────────────────────────────────────

def _cwd_matches(session_cwd: str, target_cwd: str) -> bool:
    """Codex may record a parent directory as cwd. Match if equal or ancestor."""
    return session_cwd == target_cwd or target_cwd.startswith(session_cwd + "/")


def find_codex_candidates(cwd: str, focus: str | None = None) -> list[dict]:
    """Find Codex session candidates for the given source cwd."""
    sessions_root = Path.home() / ".codex" / "sessions"
    candidates = []
    for jsonl in sessions_root.rglob("*.jsonl"):
        try:
            with open(jsonl, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if '"session_meta"' not in line and '"cwd"' not in line:
                        continue
                    try:
                        d = json.loads(line.strip())
                    except json.JSONDecodeError:
                        continue
                    if d.get("type") == "session_meta":
                        sc = d.get("payload", {}).get("cwd", "")
                        if _cwd_matches(sc, cwd):
                            candidates.append({
                                "path": jsonl,
                                "session_cwd": sc,
                                "cwd_precision": len(sc),
                                "focus_score": focus_score(jsonl, focus),
                                "mtime": _mtime(jsonl),
                            })
                        break
        except Exception:
            continue
    candidates.sort(key=lambda x: (x["cwd_precision"], x["focus_score"], x["mtime"]), reverse=True)
    return candidates


def find_codex_session(cwd: str, focus: str | None = None) -> Path | None:
    candidates = find_codex_candidates(cwd, focus)
    return candidates[0]["path"] if candidates else None


def _transcript_blocks(text: str) -> list[str]:
    """Return explicit TRANSCRIPT blocks, excluding surrounding skill examples."""
    blocks = re.findall(
        r">>> TRANSCRIPT START\s*(.*?)\s*>>> TRANSCRIPT END",
        text,
        flags=re.DOTALL,
    )
    return blocks


def extract_codex_transcript(text: str) -> list[dict]:
    """Extract [N] user:/assistant: turns from TRANSCRIPT blocks."""
    blocks = _transcript_blocks(text) or [text]
    pattern = re.compile(r'^\[(\d+)\]\s+(user|assistant):\s*(.*?)(?=^\[\d+\]\s+(?:user|assistant|tool|system|guardian|developer):|\Z)', re.MULTILINE | re.DOTALL)
    turns = []
    for block in blocks:
        block_turns = []
        for m in pattern.finditer(block):
            block_turns.append({
                "turn": int(m.group(1)),
                "role": m.group(2),
                "text": m.group(3).strip(),
            })
        # Skip the tiny illustrative example from Passdown instructions if it
        # appears in injected skill text instead of real session transcript.
        joined = "\n".join(t["text"] for t in block_turns)
        if len(block_turns) <= 3 and "我想构建一个产品" in joined and "再加一个功能" in joined:
            continue
        turns.extend(block_turns)
    # Dedup by (turn, role), keep longest. DELTA blocks are cumulative.
    seen = {}
    for t in turns:
        key = (t["turn"], t["role"])
        if key not in seen or len(t["text"]) > len(seen[key]["text"]):
            seen[key] = t
    return sorted(seen.values(), key=lambda x: (x["turn"], 0 if x["role"] == "user" else 1))


def extract_all_text_from_jsonl(path: Path) -> tuple[bool, str]:
    """Extract all text blocks from a Codex JSONL, returning (has_transcript, combined_text)."""
    has_transcript = False
    all_texts = []
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                d = json.loads(line.strip())
            except json.JSONDecodeError:
                continue
            # Check for TRANSCRIPT in raw JSON string of this line
            line_str = json.dumps(d)
            if ">>> TRANSCRIPT" in line_str:
                has_transcript = True
            # Extract text from content blocks regardless of type
            payload = d.get("payload") or {}
            content = payload.get("content") or []
            for block in content:
                text = block.get("text") or ""
                if text:
                    all_texts.append(text)

    return has_transcript, "\n".join(all_texts)


def parse_codex(path: Path) -> dict:
    """Parse a Codex session JSONL. Auto-detect TRANSCRIPT vs direct mode."""
    has_transcript, combined = extract_all_text_from_jsonl(path)
    total_lines = sum(1 for _ in open(path, encoding="utf-8", errors="ignore"))

    if has_transcript:
        turns = extract_codex_transcript(combined)
        if turns:
            return {
                "mode": "transcript",
                "total_lines": total_lines,
                "turns": turns,
            }

    # Direct mode fallback when no transcript exists or only injected examples were found
    turns = []
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                d = json.loads(line.strip())
            except json.JSONDecodeError:
                continue
            t = d.get("type", "")
            payload = d.get("payload") or {}
            role = payload.get("role", "")
            if t != "response_item" or role not in ("user", "assistant"):
                continue
            content = payload.get("content") or []
            texts = []
            for block in content:
                btype = block.get("type", "")
                text = block.get("text") or ""
                if btype in ("input_text", "output_text") and text:
                    texts.append(text)
            if texts:
                combined_text = "\n".join(texts)
                if looks_like_raw_context_dump(combined_text):
                    continue
                if role == "assistant" and combined_text.strip().startswith('{"outcome"'):
                    continue
                turns.append({"role": role, "text": combined_text})

    return {
        "mode": "direct",
        "total_lines": total_lines,
        "turns": turns,
    }


# ── Pi ─────────────────────────────────────────────────────────────────────

def find_pi_candidates(cwd: str, focus: str | None = None) -> list[dict]:
    """Find Pi session candidates for the given source cwd."""
    slug = slugify_pi(cwd)
    sessions_dir = Path.home() / ".pi" / "agent" / "sessions" / slug
    if not sessions_dir.is_dir():
        return []
    candidates = []
    for f in sessions_dir.glob("*.jsonl"):
        candidates.append({
            "path": f,
            "focus_score": focus_score(f, focus),
            "mtime": _mtime(f),
            "size": f.stat().st_size if f.exists() else 0,
        })
    candidates.sort(key=lambda x: (x["focus_score"], x["mtime"], x["size"]), reverse=True)
    return candidates


def find_pi_session(cwd: str, focus: str | None = None) -> Path | None:
    candidates = find_pi_candidates(cwd, focus)
    return candidates[0]["path"] if candidates else None


def parse_pi(path: Path) -> dict:
    """Parse a Pi session JSONL."""
    turns = []
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                d = json.loads(line.strip())
            except json.JSONDecodeError:
                continue
            t = d.get("type", "")
            if t != "message":
                continue
            msg = d.get("message") or {}
            role = msg.get("role", "")
            if role not in ("user", "assistant"):
                continue
            content = msg.get("content") or []
            texts = []
            for block in content:
                if block.get("type") == "text":
                    text = block.get("text") or ""
                    if text:
                        texts.append(text)
            if texts:
                turns.append({"role": role, "text": "\n".join(texts)})

    return {
        "mode": "message",
        "total_lines": sum(1 for _ in open(path, encoding="utf-8", errors="ignore")),
        "turns": turns,
    }


# ── Claude Code ─────────────────────────────────────────────────────────────

def _count_turns(jsonl_path: Path) -> int:
    """Count user/assistant turns in a JSONL for quality scoring."""
    try:
        count = 0
        with open(jsonl_path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                if '"type":"user"' in line or '"type":"assistant"' in line:
                    count += 1
        return count
    except Exception:
        return 0


def find_claude_candidates(cwd: str, focus: str | None = None) -> list[dict]:
    """Find the most recent Claude Code session for the given cwd.

    Tries ~/.claude/sessions/*.json index first. Falls back to direct
    scan of ~/.claude/projects/<cwd-slug>/*.jsonl when the index has
    no entry for this cwd (common when sessions are started from
    different CLI invocations or the index wasn't written).
    """
    # ── Primary: session index ───────────────────────────
    sessions_dir = Path.home() / ".claude" / "sessions"
    best_ts = 0
    best_id = None
    if sessions_dir.is_dir():
        for session_file in sessions_dir.glob("*.json"):
            try:
                meta = json.loads(session_file.read_text(encoding="utf-8"))
                if meta.get("cwd") == cwd:
                    ts = meta.get("startedAt", 0)
                    if ts > best_ts:
                        best_ts = ts
                        best_id = meta.get("sessionId")
            except Exception:
                continue

    slug = slugify_claude(cwd)
    project_dir = Path.home() / ".claude" / "projects" / slug

    candidates = []
    if best_id:
        candidate = project_dir / f"{best_id}.jsonl"
        if candidate.is_file():
            candidates.append({
                "path": candidate,
                "turns": _count_turns(candidate),
                "focus_score": focus_score(candidate, focus),
                "mtime": _mtime(candidate),
                "index_match": 1,
            })

    # ── Fallback: scan project directory directly ──────────
    if project_dir.is_dir():
        for jsonl in project_dir.glob("*.jsonl"):
            if best_id and jsonl.name == f"{best_id}.jsonl":
                continue
            turns = _count_turns(jsonl)
            candidates.append({
                "path": jsonl,
                "turns": turns,
                "focus_score": focus_score(jsonl, focus),
                "mtime": _mtime(jsonl),
                "index_match": 0,
            })

    candidates.sort(key=lambda x: (x["index_match"], x["focus_score"], x["turns"] >= 5, x["mtime"]), reverse=True)
    return candidates


def find_claude_session(cwd: str, focus: str | None = None) -> Path | None:
    candidates = find_claude_candidates(cwd, focus)
    return candidates[0]["path"] if candidates else None


def parse_claude(path: Path) -> dict:
    """Parse a Claude Code session JSONL."""
    turns = []
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                d = json.loads(line.strip())
            except json.JSONDecodeError:
                continue
            t = d.get("type", "")
            if t == "user":
                msg = d.get("message") or {}
                text = msg.get("content", "")
                if text:
                    turns.append({"role": "user", "text": str(text)})
            elif t == "assistant":
                msg = d.get("message") or {}
                content = msg.get("content") or []
                texts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text") or ""
                        if text:
                            texts.append(text)
                if texts:
                    turns.append({"role": "assistant", "text": "\n".join(texts)})

    return {
        "mode": "message",
        "total_lines": sum(1 for _ in open(path, encoding="utf-8", errors="ignore")),
        "turns": turns,
    }


# ── CLI ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Extract handoff context from coding agent sessions")
    parser.add_argument("--former", choices=["codex", "pi", "claude"], help="Alias for --source (preferred in handoff context)")
    parser.add_argument("--source", choices=["codex", "pi", "claude"], help="Which agent session to read")
    parser.add_argument("--cwd", help="Source working directory to match sessions")
    parser.add_argument("--dir", dest="source_dir", help="Alias for --cwd; useful for cross-directory handoff")
    parser.add_argument("--file", help="Direct session JSONL path; bypass session discovery")
    parser.add_argument("--focus", help="Topic used to rank candidate sessions and guide compression")
    parser.add_argument("--json", action="store_true", help="Output raw JSON (default: human-readable)")
    args = parser.parse_args()

    source = args.former or args.source
    if not source:
        print("Error: --former (or --source) is required", file=sys.stderr)
        return 1

    source_cwd = args.source_dir or args.cwd
    if not source_cwd and not args.file:
        print("Error: --cwd/--dir is required unless --file is provided", file=sys.stderr)
        return 1

    parsers = {"codex": parse_codex, "pi": parse_pi, "claude": parse_claude}
    candidate_finders = {"codex": find_codex_candidates, "pi": find_pi_candidates, "claude": find_claude_candidates}
    parser_fn = parsers[source]

    candidates = []
    multi_session = False
    if args.file:
        session_path = Path(args.file).expanduser().resolve()
        if not session_path.is_file():
            print(f"Error: session file not found: {session_path}", file=sys.stderr)
            return 1
        session_paths = [session_path]
        total_candidates = 1
        matched = [{"path": session_path, "direct_file": True, "mtime": _mtime(session_path)}]
    else:
        candidates = candidate_finders[source](str(Path(source_cwd).expanduser().resolve()), args.focus)
        if not candidates:
            print(f"No session found for source={source} cwd={source_cwd} focus={args.focus or ''}", file=sys.stderr)
            return 1

        # When focus is active, extract from ALL matching sessions (not just top 1)
        total_candidates = len(candidates)
        if args.focus:
            # Collect all candidates with non-zero focus score
            matched = [c for c in candidates if c.get("focus_score", 0) > 0]
            if not matched:
                # Fallback: if focus matched nothing by score, use top 3
                matched = candidates[:3]
            session_paths = [c["path"] for c in matched]
            multi_session = len(session_paths) > 1
        else:
            session_paths = [candidates[0]["path"]]
            matched = [candidates[0]]

        session_path = session_paths[0]

    # Extract from all matched sessions
    all_turns = []
    modes = set()
    total_lines = 0
    for sp in session_paths:
        result = parser_fn(sp)
        mtime = _mtime(sp)
        for idx, t in enumerate(result["turns"]):
            t["session_file"] = str(sp)
            t["session_mtime"] = mtime
            t["session_ordinal"] = idx
        all_turns.extend(result["turns"])
        modes.add(result["mode"])
        total_lines += result["total_lines"]

    # Sort by session mtime then stable per-session ordinal
    all_turns.sort(key=lambda t: (t.get("session_mtime", 0), t.get("session_ordinal", 0)))

    # Deduplicate by normalized full-text hash
    seen = set()
    turns = []
    for t in all_turns:
        norm = " ".join(t["text"].lower().split())
        key = hashlib.sha256(norm.encode()).digest()
        if key not in seen:
            seen.add(key)
            turns.append(t)

    total_words = sum(len(t["text"].split()) for t in turns)
    total_tokens = sum(estimate_tokens(t["text"]) for t in turns)

    output = {
        "source": source,
        "current_cwd": str(Path.cwd().resolve()),
        "source_cwd": str(Path(source_cwd).expanduser().resolve()) if source_cwd else None,
        "focus": args.focus,
        "multi_session": multi_session,
        "matched_sessions": len(session_paths),
        "session_file": str(session_path),
        "session_files": [str(p) for p in session_paths],
        "candidate_count": total_candidates,
        "candidates": [
            {k: (str(v) if isinstance(v, Path) else v) for k, v in c.items()}
            for c in matched[:20]
        ],
        "mode": ", ".join(sorted(modes)),
        "total_lines": total_lines,
        "extracted_turns": len(turns),
        "estimated_words": total_words,
        "estimated_tokens": total_tokens,
        "turns": turns,
    }

    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"source:       {output['source']}")
        print(f"current cwd:  {output['current_cwd']}")
        print(f"source cwd:   {output['source_cwd'] or '-'}")
        print(f"focus:        {output['focus'] or '-'}")
        if output['multi_session']:
            print(f"matched:      {output['matched_sessions']} sessions (focus hit)")
            for sf in output['session_files']:
                print(f"  - {sf}")
        else:
            print(f"session:      {output['session_file']}")
        print(f"candidates:   {output['candidate_count']}")
        print(f"mode:         {output['mode']}")
        print(f"lines:        {output['total_lines']}")
        print(f"turns:        {output['extracted_turns']}")
        print(f"words:        ~{output['estimated_words']}")
        print(f"tokens:       ~{output['estimated_tokens']}")
        print(f"{'─'*60}")
        for i, turn in enumerate(turns):
            role = turn["role"]
            text = turn["text"]
            if role == "user":
                print(f"\n[{i}] USER: {text[:300]}{'...' if len(text) > 300 else ''}")
            else:
                print(f"[{i}] ASSISTANT: {text[:400]}{'...' if len(text) > 400 else ''}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
