#!/usr/bin/env python3
"""Extract filtered conversation turns from Codex / Pi / Claude Code JSONL sessions.

Usage:
  python extract_handoff.py --former codex --cwd /path/to/project
  python extract_handoff.py --former pi    --dir /path/to/project --focus "bug repair"
  python extract_handoff.py --former claude --file /path/to/session.jsonl
  python extract_handoff.py --session <uuid> --dir /path/to/project

Output: JSON with session metadata, token estimate, filtered turns, and candidate info.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import warnings
from pathlib import Path


DEFAULT_MAX_TOKENS = 8_000
DECISION_MARKERS = (
    "决定", "结论", "批准", "拒绝", "保留", "删除", "下一步", "未完成",
    "decision", "approved", "rejected", "keep", "remove", "next step",
    "pending", "must", "do not",
)


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


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


def truncate_text(text: str, max_tokens: int) -> str:
    """Keep the beginning and end of an oversized turn within a hard budget."""
    if estimate_tokens(text) <= max_tokens:
        return text
    max_chars = max_tokens * 3
    marker = "\n...[turn truncated to handoff budget]...\n"
    if max_chars <= len(marker) + 2:
        return text[:max_chars]
    body_chars = max_chars - len(marker)
    head_chars = body_chars // 2
    tail_chars = body_chars - head_chars
    return text[:head_chars].rstrip() + marker + text[-tail_chars:].lstrip()


def truncate_around_match(text: str, offset: int, length: int, max_tokens: int) -> str:
    """Keep the indexed passage when compressing an oversized turn."""
    if estimate_tokens(text) <= max_tokens:
        return text
    max_chars = max_tokens * 3
    marker = "\n...[turn truncated to handoff budget]...\n"
    body_chars = max_chars - 2 * len(marker)
    if body_chars <= 0:
        body_chars = max_chars
        marker = ""
    center = offset + min(length, max(0, len(text) - offset)) // 2
    start = max(0, min(len(text) - body_chars, center - body_chars // 2))
    end = min(len(text), start + body_chars)
    return (marker if start else "") + text[start:end] + (marker if end < len(text) else "")


def _focus_terms(focus: str | None) -> list[str]:
    if not focus:
        return []
    return [t.lower() for t in re.split(r"\s+", focus.strip()) if t.strip()]


def _decompress_zstd(path: Path) -> str | None:
    """Decompress a .zstd session file, preferring the zstandard module and
    falling back to the zstd CLI. Returns None when neither is available."""
    try:
        import zstandard  # type: ignore

        with open(path, "rb") as f:
            reader = zstandard.ZstdDecompressor().stream_reader(f)
            try:
                return reader.read().decode("utf-8", errors="ignore")
            finally:
                reader.close()
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["zstd", "-dc", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout
    except Exception:
        pass
    return None


def keyword_occurrences(term: str, text: str) -> int:
    """Match structured identifiers on token boundaries, not as prefixes."""
    if re.search(r"[0-9_./:+-]", term):
        pattern = (r"(?<![a-z0-9_./:+-])" + re.escape(term) +
                   r"(?![a-z0-9_]|[./:+-](?=[a-z0-9_]))")
        return sum(1 for _ in re.finditer(pattern, text))
    return text.count(term)


def focus_score(path: Path, focus: str | None, runtime: str) -> int:
    """Score only the same conversation turns eligible for handoff."""
    terms = _focus_terms(focus)
    if not terms:
        return 0
    parsers = {"codex": parse_codex, "pi": parse_pi, "claude": parse_claude, "dsh": parse_dsh}
    try:
        turns = parsers[runtime](path)["turns"]
        return sum(keyword_occurrences(term, turn["text"].lower()) * max(1, len(term))
                   for turn in turns for term in terms)
    except Exception:
        return 0


# Grammatical scaffolding does not describe the subject of a history search.
KEYWORD_STOPWORDS = frozenset({
    "为什么", "怎么", "如何", "是否", "怎样", "什么", "哪些", "先前",
    "已经", "我们", "用户", "这个", "那个", "the", "and", "for",
    "how", "what", "why", "does", "was", "were", "with", "can",
})


def keyword_tokens(focus: str) -> tuple[list[str], str]:
    """Tokenize query only; identifiers remain intact and the fallback is offline."""
    parts = re.findall(r"[a-z0-9_./:+-]+|[\u4e00-\u9fff]+", focus.lower())

    def split(cut):
        tokens = []
        for part in parts:
            if re.fullmatch(r"[\u4e00-\u9fff]+", part):
                words = [x for x in cut(part) if len(x) > 1 and x not in KEYWORD_STOPWORDS]
                if not words and 1 < len(part) <= 3 and part not in KEYWORD_STOPWORDS:
                    words = [part]
                tokens.extend(words)
            elif part not in KEYWORD_STOPWORDS:
                tokens.append(part)
        return list(dict.fromkeys(tokens)) or ([focus.strip().lower()] if focus.strip() else [])

    try:
        import jieba
        jieba.setLogLevel("ERROR")
        return split(lambda text: jieba.cut(text, HMM=False)), "jieba"
    except Exception:
        return split(lambda text: [text]), "literal_fallback"


def automation_context(turn: dict) -> dict | None:
    """Recognize the scheduler's four-line wrapper without indexing its prompt."""
    if turn.get("role") != "user":
        return None
    lines = turn.get("text", "").splitlines()
    prefixes = ("Automation: ", "Automation ID: ", "Automation memory: ", "Last run: ")
    if len(lines) < 4 or not all(lines[i].startswith(p) for i, p in enumerate(prefixes)):
        return None
    name, identifier = lines[0][len(prefixes[0]):].strip(), lines[1][len(prefixes[1]):].strip()
    if not name or not re.fullmatch(r"[a-zA-Z0-9_.-]+", identifier):
        return None
    return {"name": name, "id": identifier}


def rank_keyword_candidates(candidates: list[dict], focus: str) -> dict:
    """Score allowed turns and tightly bounded adjacent question/answer pairs."""
    tokens, tokenizer = keyword_tokens(focus)
    parsers = {"codex": parse_codex, "pi": parse_pi, "claude": parse_claude, "dsh": parse_dsh}
    docs = {}
    failed = 0
    for c in candidates:
        key = (str(c["path"]), c["runtime"])
        if key in docs:
            continue
        try:
            turns = parsers[c["runtime"]](c["path"])["turns"]
            entries = []
            context = None
            for turn in turns:
                info = automation_context(turn)
                if info:
                    context = info
                    entries.append(("automation", "", info["id"].lower()))
                    continue
                role = turn["role"]
                if role == "user":
                    context = None
                text = turn["text"].lower()
                identifier = context["id"].lower() if role == "assistant" and context else None
                entries.append((role, text, identifier))
            docs[key] = entries
        except Exception:
            docs[key] = None
            failed += 1
    def contains(term, text, identifier):
        if identifier == term:
            return True
        return keyword_occurrences(term, text) > 0

    valid_docs = [turns for turns in docs.values() if turns is not None]
    count = len(valid_docs)
    frequency = {t: sum(any(contains(t, text, identifier) for _, text, identifier in turns) for turns in valid_docs) for t in tokens}
    distinctive = [t for t in tokens if frequency[t] <= count / 2]
    active = distinctive or tokens
    mixed_script = bool(re.search(r"[\u4e00-\u9fff]", focus))
    mandatory = [t for t in distinctive if re.fullmatch(r"[a-z0-9_./:+-]+", t)
                 and (mixed_script or re.search(r"[0-9_./:+-]", t))]
    needed = min(2, len(active))
    weights = {t: math.log((count + 1) / (frequency[t] + 1)) + 1 for t in active}
    context_terms = [t for t in tokens if t not in active]
    rare = {t for t in active if frequency[t] <= max(1, count / 5)}
    for c in candidates:
        c.pop("keyword_ordinal", None)
        c.pop("keyword_ordinals", None)
        c.pop("keyword_match", None)
        c.pop("keyword_context_matches", None)
        entries = docs[(str(c["path"]), c["runtime"])] or []
        score = 0.0
        best = []
        context_matches = 0
        match_kind = None
        for ordinal, (role, text, identifier) in enumerate(entries):
            if role == "automation":
                continue
            found = {t for t in active if contains(t, text, identifier)}
            if len(found) >= needed and all(t in found for t in mandatory):
                value = sum(weights[t] for t in found)
                extra = sum(contains(t, text, identifier) for t in context_terms)
                if (value, extra) > (score, context_matches):
                    score, context_matches, best, match_kind = value, extra, [ordinal], "turn"
        for ordinal in range(len(entries) - 1):
            role_a, text_a, id_a = entries[ordinal]
            role_b, text_b, id_b = entries[ordinal + 1]
            if role_a != "user" or role_b != "assistant":
                continue
            left = {t for t in active if contains(t, text_a, id_a)}
            right = {t for t in active if contains(t, text_b, id_b)}
            found = left | right
            # Both sides must contribute different rare terms; this prevents
            # common words from joining unrelated adjacent messages.
            if (len(found) >= needed and all(t in found for t in mandatory)
                    and (left - right) & rare and (right - left) & rare):
                value = sum(weights[t] for t in found)
                extra = sum(contains(t, text_a, id_a) or contains(t, text_b, id_b) for t in context_terms)
                if (value, extra) > (score, context_matches):
                    score, context_matches, best, match_kind = value, extra, [ordinal, ordinal + 1], "adjacent"
        # An interrupted run can still be found by its exact ID even when it
        # produced no assistant turn; this is metadata, not a result.
        if not best and len(tokens) == 1:
            if any(role == "automation" and identifier == tokens[0] for role, text, identifier in entries):
                score, match_kind = weights.get(tokens[0], 1.0), "metadata"
        c["focus_score"] = round(score, 6)
        if match_kind:
            if best:
                c["keyword_ordinal"] = best[0]
                c["keyword_ordinals"] = best
            c["keyword_match"] = match_kind
            c["keyword_context_matches"] = context_matches
    return {"tokenizer": tokenizer, "tokens": tokens, "active_terms": active, "mandatory_terms": mandatory,
            "sessions": count, "parse_failed": failed}


# -- zvec retriever ---------------------------------------------------------

EMBEDDING_DIM = 384
DEFAULT_ZVEC_INDEX = Path.home() / ".agents" / "passdown-zvec-index"


def passdown_zvec_path() -> Path:
    return Path(os.environ.get("PASSDOWN_ZVEC_PATH", str(DEFAULT_ZVEC_INDEX))).expanduser()


def token_features(text: str) -> list[str]:
    lowered = text.lower()
    tokens = re.findall(r"[a-z0-9_./:-]+|[一-鿿]", lowered)
    feats = list(tokens)
    feats.extend("".join(tokens[i:i + 2]) for i in range(max(0, len(tokens) - 1)))
    for word in re.findall(r"[a-z0-9_./:-]{4,}", lowered):
        feats.extend(word[i:i + 4] for i in range(len(word) - 3))
    return feats


def turn_focus_score(text: str, focus: str | None) -> int:
    """Score turn relevance with the same multilingual features used by zvec."""
    if not focus:
        return 0
    query_features = set(token_features(focus))
    if not query_features:
        return 0
    return len(query_features.intersection(token_features(text)))


def decision_score(text: str) -> int:
    lowered = text.lower()
    return sum(marker in lowered for marker in DECISION_MARKERS)


def budget_turns(
    turns: list[dict], focus: str | None, max_tokens: int
) -> tuple[list[dict], dict]:
    """Select a compact chronological handoff while enforcing max_tokens.

    Priority is current state, initial context, focus hits, explicit
    decisions/next steps, then the remaining recent turns.
    """
    original_tokens = sum(estimate_tokens(turn["text"]) for turn in turns)
    base_stats = {
        "max_tokens": max_tokens,
        "source_turns": len(turns),
        "source_estimated_tokens": original_tokens,
    }
    if original_tokens <= max_tokens:
        selected = [dict(turn) for turn in turns]
        return selected, {
            **base_stats,
            "budget_applied": False,
            "dropped_turns": 0,
            "truncated_turns": 0,
        }

    count = len(turns)
    recent = list(range(max(0, count - 3), count))[::-1]
    initial = list(range(min(2, count)))

    focus_scores = [
        (turn_focus_score(turn["text"], focus), index)
        for index, turn in enumerate(turns)
    ]
    focused = [
        index
        for score, index in sorted(
            focus_scores, key=lambda item: (item[0], item[1]), reverse=True
        )
        if score > 0
    ]
    focused = [i for i, turn in enumerate(turns) if turn.get("keyword_hit") or turn.get("semantic_hit")] + focused

    decision_scores = [
        (decision_score(turn["text"]), index)
        for index, turn in enumerate(turns)
    ]
    decisions = [
        index
        for score, index in sorted(
            decision_scores, key=lambda item: (item[0], item[1]), reverse=True
        )
        if score > 0
    ]
    priority = recent + initial + focused + decisions + list(range(count - 1, -1, -1))

    per_turn_budget = max(16, min(1_200, max_tokens // 8))
    remaining = max_tokens
    selected_by_index: dict[int, dict] = {}
    for index in priority:
        if index in selected_by_index or remaining <= 0:
            continue
        turn_budget = min(per_turn_budget, remaining)
        original = turns[index]
        offset = original.get("semantic_offset")
        if isinstance(offset, int) and 0 <= offset < len(original["text"]):
            clipped_text = truncate_around_match(original["text"], offset, 600, turn_budget)
        else:
            clipped_text = truncate_text(original["text"], turn_budget)
        candidate = dict(original)
        candidate["text"] = clipped_text
        if clipped_text != original["text"]:
            candidate["text_truncated"] = True
            if isinstance(offset, int) and 0 <= offset < len(original["text"]):
                marker_size = len("\n...[turn truncated to handoff budget]...\n")
                capacity = turn_budget * 3 - 2 * marker_size
                if capacity <= 0:
                    capacity = turn_budget * 3
                if capacity < min(600, len(original["text"]) - offset):
                    candidate["semantic_passage_truncated"] = True
        cost = estimate_tokens(clipped_text)
        if cost > remaining:
            continue
        selected_by_index[index] = candidate
        remaining -= cost

    selected = [selected_by_index[index] for index in sorted(selected_by_index)]
    return selected, {
        **base_stats,
        "budget_applied": True,
        "dropped_turns": count - len(selected),
        "truncated_turns": sum(
            bool(turn.get("text_truncated")) for turn in selected
        ),
    }


def embed_text(text: str) -> list[float]:
    vec = [0.0] * EMBEDDING_DIM
    for feat in token_features(text):
        digest = hashlib.blake2b(feat.encode("utf-8"), digest_size=8).digest()
        n = int.from_bytes(digest, "little")
        idx = n % EMBEDDING_DIM
        sign = 1.0 if (n >> 63) == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def _load_zvec_metadata(index_path: Path) -> dict[str, dict]:
    sidecar = index_path / "metadata.jsonl"
    if not sidecar.exists():
        return {}
    metadata: dict[str, dict] = {}
    with sidecar.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                meta = json.loads(line)
            except json.JSONDecodeError:
                continue
            doc_id = meta.get("id")
            preview = meta.get("text_preview") or ""
            lines = preview.splitlines() if isinstance(preview, str) else []
            # Old sidecars truncate previews, sometimes before the fourth header.
            automation_preview = (meta.get("role") == "user" and len(lines) >= 3
                                  and lines[0].startswith("Automation: ")
                                  and lines[1].startswith("Automation ID: ")
                                  and lines[2].startswith("Automation memory: "))
            if doc_id and not automation_preview:
                metadata[doc_id] = meta
    return metadata


def _codex_session_cwd(path: Path) -> str:
    try:
        with path.open(encoding="utf-8", errors="ignore") as f:
            for line in f:
                if '"session_meta"' not in line and '"cwd"' not in line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if data.get("type") == "session_meta":
                    return data.get("payload", {}).get("cwd", "")
    except OSError:
        return ""
    return ""


def _metadata_matches_sources(meta: dict, source_dirs: list[str]) -> bool:
    source_cwd = meta.get("source_cwd")
    if source_cwd:
        return any(_cwd_matches(str(source_cwd), src) or _cwd_matches(src, str(source_cwd)) for src in source_dirs)

    session_file = meta.get("session_file", "")
    runtime = meta.get("runtime", "")
    path = Path(session_file)
    if runtime == "claude":
        return any(path.parent.name == slugify_claude(src) for src in source_dirs)
    if runtime == "pi":
        return any(path.parent.name == slugify_pi(src) for src in source_dirs)
    if runtime == "dsh":
        return any(path.parent.parent.name == slugify_dsh(src) for src in source_dirs)
    if runtime == "codex":
        cwd = _codex_session_cwd(path)
        return bool(cwd) and any(_cwd_matches(cwd, src) for src in source_dirs)
    return False


def codex_session_files(include_archived: bool = False):
    roots = [Path.home() / ".codex" / "sessions"]
    if include_archived:
        roots.append(Path.home() / ".codex" / "archived_sessions")
    for root in roots:
        yield from root.rglob("*.jsonl")


def is_archived_codex_path(path: Path) -> bool:
    return path.resolve().is_relative_to(Path.home() / ".codex" / "archived_sessions")


def resolve_indexed_codex_path(path: Path, include_archived: bool, cache: dict) -> Path | None:
    """Resolve archive/unarchive moves by exact rollout filename, without index writes."""
    if path.is_file():
        return path if include_archived or not is_archived_codex_path(path) else None
    roots = [Path.home() / ".codex" / name for name in ("sessions", "archived_sessions")]
    if not any(path.is_relative_to(root) for root in roots):
        return None
    if "by_name" not in cache:
        by_name = {}
        for candidate in codex_session_files(include_archived):
            by_name.setdefault(candidate.name, []).append(candidate)
        cache["by_name"] = by_name
    matches = cache["by_name"].get(path.name, [])
    return matches[0] if len(matches) == 1 else None


def find_zvec_candidates(source_dirs: list[str], runtimes: list[str], focus: str | None, top_k: int = 80, min_sessions: int = 20, include_archived: bool = False) -> list[dict]:
    """Return Passdown session candidates from zvec.

    zvec is only a retriever. Candidates still point at original JSONL files;
    parsing and handoff generation remain owned by this extractor.
    """
    if not focus:
        return []
    index_path = passdown_zvec_path()
    if not index_path.exists():
        return []
    try:
        import zvec  # type: ignore
    except Exception:
        return []

    metadata = _load_zvec_metadata(index_path)
    if not metadata:
        return []

    try:
        collection = zvec.open(path=str(index_path))
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            results = collection.query(
                zvec.VectorQuery("text_embedding", vector=embed_text(focus)),
                topk=top_k,
            )
    except Exception:
        return []

    runtime_set = set(runtimes)
    session_scores: dict[str, float] = {}
    session_chunks: dict[str, list[dict]] = {}
    session_sample: dict[str, dict] = {}
    path_cache = {}
    for result in results:
        meta = metadata.get(result.id)
        if not meta:
            continue
        runtime = meta.get("runtime", "")
        if runtime_set and runtime not in runtime_set:
            continue
        session_file = meta.get("session_file")
        if not session_file:
            continue
        path = Path(session_file)
        if runtime == "codex":
            path = resolve_indexed_codex_path(path, include_archived, path_cache)
        if path is None or not path.is_file():
            continue
        session_file = str(path)
        meta = {**meta, "session_file": session_file}
        if not _metadata_matches_sources(meta, source_dirs):
            continue
        score = float(getattr(result, "score", 0.0))
        session_scores[session_file] = session_scores.get(session_file, 0.0) + score
        session_chunks.setdefault(session_file, []).append({
            "chunk_id": result.id,
            "score": score,
            "role": meta.get("role", ""),
            "turn_index": meta.get("turn_index", 0),
            "text_preview": meta.get("text_preview", ""),
        })
        session_sample.setdefault(session_file, meta)

    candidates = []
    for session_file, agg_score in sorted(session_scores.items(), key=lambda x: x[1], reverse=True)[:min_sessions]:
        sample = session_sample.get(session_file, {})
        path = Path(session_file)
        runtime = sample.get("runtime", "")
        source_cwd = sample.get("source_cwd", "")
        focus_rank = max(1, int(abs(agg_score) * 1_000_000))
        candidates.append({
            "path": path,
            "runtime": runtime,
            "source_cwd": source_cwd,
            "focus_score": focus_rank,
            "zvec_score": round(agg_score, 6),
            "zvec_chunks": len(session_chunks.get(session_file, [])),
            "mtime": float(sample.get("session_mtime") or _mtime(path)),
        })
    candidates.sort(key=lambda c: (c.get("zvec_score", 0), c.get("mtime", 0)), reverse=True)
    return candidates


def _session_stamp(path: Path) -> str | None:
    try:
        stat = path.stat()
        return f"{stat.st_dev}:{stat.st_ino}:{stat.st_size}:{stat.st_mtime_ns}"
    except OSError:
        return None


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0


def _line_count(path: Path) -> int:
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
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


def find_codex_candidates(cwd: str, focus: str | None = None, include_archived: bool = False) -> list[dict]:
    """Find Codex session candidates for the given source cwd."""
    candidates = []
    for jsonl in codex_session_files(include_archived):
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
                                "focus_score": focus_score(jsonl, focus, "codex"),
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
    """Read transcript wrappers from user input, never from tool output."""
    all_texts = []
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                d = json.loads(line.strip())
            except json.JSONDecodeError:
                continue
            payload = d.get("payload") or {}
            if d.get("type") == "response_item" and payload.get("role") == "user":
                for block in payload.get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "input_text":
                        text = block.get("text") or ""
                        if ">>> TRANSCRIPT" in text:
                            all_texts.append(text)
            elif d.get("type") == "event_msg" and payload.get("type") == "user_message":
                text = payload.get("message") or ""
                if isinstance(text, str) and ">>> TRANSCRIPT" in text:
                    all_texts.append(text)
    return bool(all_texts), "\n".join(all_texts)


def parse_codex(path: Path) -> dict:
    """Parse a Codex session JSONL. Auto-detect TRANSCRIPT vs direct mode."""
    has_transcript, combined = extract_all_text_from_jsonl(path)
    total_lines = _line_count(path)

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
            "focus_score": focus_score(f, focus, "pi"),
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
        "total_lines": _line_count(path),
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
                "focus_score": focus_score(candidate, focus, "claude"),
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
                "focus_score": focus_score(jsonl, focus, "claude"),
                "mtime": _mtime(jsonl),
                "index_match": 0,
            })

    candidates.sort(key=lambda x: (x["index_match"], x["focus_score"], x["turns"] >= 5, x["mtime"]), reverse=True)
    return candidates


def find_claude_session(cwd: str, focus: str | None = None) -> Path | None:
    candidates = find_claude_candidates(cwd, focus)
    return candidates[0]["path"] if candidates else None


def _looks_like_claude_noise(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    noise_markers = [
        "<local-command-caveat>",
        "<local-command-stdout>",
        "<local-command-stderr>",
        "<command-name>",
        "<command-message>",
        "<command-args>",
    ]
    if any(marker in stripped for marker in noise_markers):
        return True
    if stripped.startswith("[{'tool_use_id'") or stripped.startswith('[{"tool_use_id"'):
        return True
    if stripped.startswith("[{'type': 'tool_result'") or stripped.startswith('[{"type": "tool_result"'):
        return True
    return looks_like_raw_context_dump(stripped)


def _extract_claude_user_text(content) -> str:
    """Extract only human-authored text from Claude user messages.

    Claude JSONL stores tool_result and local command events as user messages.
    Those are execution noise, not handoff conversation, so keep only plain
    text blocks and strings that are not local-command wrappers.
    """
    texts: list[str] = []
    if isinstance(content, str):
        texts = [content]
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, str):
                texts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                value = block.get("text") or ""
                if value:
                    texts.append(value)
    clean = []
    for value in texts:
        value = str(value)
        if not _looks_like_claude_noise(value):
            clean.append(value.strip())
    return "\n".join(clean).strip()


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
                text = _extract_claude_user_text(msg.get("content", ""))
                if text:
                    turns.append({"role": "user", "text": text})
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
        "total_lines": _line_count(path),
        "turns": turns,
    }


# ── DSH (DeepSeek Harness) ─────────────────────────────────────────────────

def slugify_dsh(cwd: str) -> str:
    """DSH cwd encoding: same --wrap-- convention as Pi."""
    return slugify_pi(cwd)


def find_dsh_candidates(cwd: str, focus: str | None = None) -> list[dict]:
    """Find DSH session candidates for the given source cwd.

    Sessions live at ~/.dsh/sessions/<slug>/<session-id>/session.jsonl.zstd —
    zstd-compressed JSONL, keyed by session-id directories.
    """
    slug = slugify_dsh(cwd)
    sessions_dir = Path.home() / ".dsh" / "sessions" / slug
    if not sessions_dir.is_dir():
        return []
    candidates = []
    for session_dir in sessions_dir.iterdir():
        if not session_dir.is_dir():
            continue
        jsonl = session_dir / "session.jsonl.zstd"
        if not jsonl.is_file():
            continue
        candidates.append({
            "path": jsonl,
            "session_id": session_dir.name,
            "focus_score": focus_score(jsonl, focus, "dsh"),
            "mtime": _mtime(jsonl),
        })
    candidates.sort(key=lambda x: (x["focus_score"], x["mtime"]), reverse=True)
    return candidates


def find_dsh_session(cwd: str, focus: str | None = None) -> Path | None:
    candidates = find_dsh_candidates(cwd, focus)
    return candidates[0]["path"] if candidates else None


def parse_dsh(path: Path) -> dict:
    """Parse a DSH session JSONL (zstd-compressed).

    User turns come from user/message events with source.kind == "user";
    plugin and agent-instructions injections (policy notices, injected
    instructions) are dropped. Assistant turns come from assistant/message
    events; reasoning blocks are dropped, only text blocks are kept.
    Turns are ordered by event seq.
    """
    text = _decompress_zstd(path)
    if text is None:
        return {"mode": "dsh", "total_lines": 0, "turns": []}

    sequenced: list[tuple[int, dict]] = []
    for line in text.splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        seq = d.get("seq", 0)
        etype = d.get("type", "")
        data = d.get("data") or {}

        if etype == "user/message":
            if data.get("role") != "user":
                continue
            if (data.get("source") or {}).get("kind") != "user":
                continue
            texts = [
                block.get("text", "")
                for block in (data.get("content") or [])
                if isinstance(block, dict) and block.get("type") == "text"
            ]
        elif etype == "assistant/message":
            message = data.get("message") or {}
            if message.get("role") != "assistant":
                continue
            texts = [
                block.get("text", "")
                for block in (message.get("content") or [])
                if isinstance(block, dict) and block.get("type") == "text"
            ]
        else:
            continue

        joined = "\n".join(t for t in texts if t).strip()
        if not joined:
            continue
        role = "user" if etype == "user/message" else "assistant"
        sequenced.append((seq, {"role": role, "text": joined}))

    sequenced.sort(key=lambda item: item[0])
    return {
        "mode": "dsh",
        "total_lines": len(text.splitlines()),
        "turns": [turn for _, turn in sequenced],
    }


# ── Session ID resolution ──────────────────────────────────────────────────

def resolve_session_by_id(session_id: str, source_dirs: list[str], runtimes: list[str]) -> tuple[Path, str] | None:
    """Find a session file by ID across runtime directories.

    Returns (path, runtime) or None. Searches runtimes in order; first match wins.
    """
    for src_dir in source_dirs:
        for rt in runtimes:
            path = _resolve_session_for_runtime(session_id, src_dir, rt)
            if path and path.is_file():
                return path, rt
    return None


def _resolve_session_for_runtime(session_id: str, src_dir: str, runtime: str) -> Path | None:
    if runtime == "claude":
        slug = slugify_claude(src_dir)
        candidate = Path.home() / ".claude" / "projects" / slug / f"{session_id}.jsonl"
        if candidate.is_file():
            return candidate
        project_dir = Path.home() / ".claude" / "projects" / slug
        if project_dir.is_dir():
            for f in sorted(project_dir.glob("*.jsonl"), key=_mtime, reverse=True):
                if session_id in f.stem:
                    return f
    elif runtime == "codex":
        for f in sorted(codex_session_files(include_archived=True), key=_mtime, reverse=True):
            if session_id in f.stem:
                return f
    elif runtime == "pi":
        slug = slugify_pi(src_dir)
        candidate = Path.home() / ".pi" / "agent" / "sessions" / slug / f"{session_id}.jsonl"
        if candidate.is_file():
            return candidate
        sessions_dir = Path.home() / ".pi" / "agent" / "sessions" / slug
        if sessions_dir.is_dir():
            for f in sorted(sessions_dir.glob("*.jsonl"), key=_mtime, reverse=True):
                if session_id in f.stem:
                    return f
    elif runtime == "dsh":
        slug = slugify_dsh(src_dir)
        sessions_dir = Path.home() / ".dsh" / "sessions" / slug
        if sessions_dir.is_dir():
            for f in sorted(sessions_dir.glob("*/*.zstd"), key=_mtime, reverse=True):
                if session_id in f.parent.name:
                    return f
    return None


# ── CLI ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Extract handoff context from coding agent sessions")
    parser.add_argument("--former", help="Source agent(s): codex,pi,claude,dsh (comma-separated). Auto-detect if omitted.")
    parser.add_argument("--source", help="Alias for --former")
    parser.add_argument("--cwd", action="append", help="Source working directory (repeatable, comma-separated). Default: current cwd")
    parser.add_argument("--dir", dest="source_dir", action="append", help="Alias for --cwd")
    parser.add_argument("--file", help="Direct session JSONL path; bypass session discovery")
    parser.add_argument("--session", help="Session ID (UUID/filename stem); lookup in runtime dirs, bypass discovery")
    parser.add_argument("--archived", action="store_true", help="Include archived Codex sessions in search (explicit --session always searches both stores)")
    parser.add_argument("--focus", help="Topic used to rank candidate sessions and guide compression")
    parser.add_argument("--retriever", choices=("auto", "keyword", "zvec"), default="auto", help="auto combines local semantic candidates with keyword search, and falls back to keyword; zvec is the legacy feature-hash index.")
    parser.add_argument("--max-tokens", type=positive_int, default=DEFAULT_MAX_TOKENS, help=f"Hard cap for extracted handoff turns (default: {DEFAULT_MAX_TOKENS})")
    parser.add_argument("--json", action="store_true", help="Output raw JSON (default: human-readable)")
    args = parser.parse_args()

    # Collect source directories: --dir and --cwd are both append-action lists
    raw_dirs = (args.source_dir or []) + (args.cwd or [])
    source_dirs = []
    for val in raw_dirs:
        for part in val.split(","):
            part = part.strip()
            if part:
                source_dirs.append(part)
    if not source_dirs:
        source_dirs = [os.getcwd()]
    source_dirs = [str(Path(d).expanduser().resolve()) for d in source_dirs]

    # Collect runtimes: comma-separated --former
    source = args.former or args.source
    if source:
        runtimes_to_scan = []
        for s in source.split(","):
            s = s.strip()
            if s and s not in runtimes_to_scan:
                runtimes_to_scan.append(s)
    else:
        runtimes_to_scan = ALL_RUNTIMES = ["codex", "pi", "claude", "dsh"]

    if args.retriever == "zvec" and not args.focus:
        print("Error: --retriever zvec requires --focus", file=sys.stderr)
        return 1

    parsers = {"codex": parse_codex, "pi": parse_pi, "claude": parse_claude, "dsh": parse_dsh}

    archive_scope = "including archived Codex sessions" if args.archived else "archived Codex sessions excluded; use --archived to include"
    candidates = []
    retriever_used = "file" if args.file else "keyword"
    retriever_fallback = None
    multi_session = False
    resolved_source = source or "auto"

    if args.session:
        # --session: resolve ID to file path, bypass all candidate discovery
        resolved = resolve_session_by_id(args.session, source_dirs, runtimes_to_scan)
        if resolved is None:
            rt_list = ",".join(runtimes_to_scan)
            dir_list = ",".join(source_dirs)
            print(f"Session '{args.session}' not found for source={rt_list} dirs={dir_list}", file=sys.stderr)
            return 1
        session_path, detected_runtime = resolved
        retriever_used = "session"
        resolved_source = detected_runtime
        total_candidates = 1
        matched = [{
            "path": session_path,
            "runtime": detected_runtime,
            "source_cwd": source_dirs[0],
            "direct_session": True,
            "mtime": _mtime(session_path),
        }]
        session_paths = [session_path]

    elif args.file:
        session_path = Path(args.file).expanduser().resolve()
        if not session_path.is_file():
            print(f"Error: session file not found: {session_path}", file=sys.stderr)
            return 1
        session_paths = [session_path]
        total_candidates = 1
        matched = [{"path": session_path, "direct_file": True, "mtime": _mtime(session_path)}]
    else:
        candidate_finders = {"codex": find_codex_candidates, "pi": find_pi_candidates, "claude": find_claude_candidates, "dsh": find_dsh_candidates}

        all_candidates = []
        legacy_auto = args.retriever == "auto" and os.environ.get("PASSDOWN_DISABLE_SEMANTIC") == "1"
        if args.focus and (args.retriever == "zvec" or legacy_auto):
            try:
                all_candidates = find_zvec_candidates(source_dirs, runtimes_to_scan, args.focus, include_archived=args.archived)
            except Exception as exc:
                if args.retriever == "zvec":
                    print(f"Error: zvec retriever failed: {exc}", file=sys.stderr)
                    return 1
                retriever_fallback = f"zvec_error:{exc.__class__.__name__}"
                all_candidates = []
            if all_candidates:
                retriever_used = "zvec"
            elif args.retriever == "zvec":
                rt_list = ",".join(runtimes_to_scan)
                dir_list = ",".join(source_dirs)
                print(f"No zvec session candidates for source={rt_list} dirs={dir_list} focus={args.focus}; {archive_scope}", file=sys.stderr)
                return 1
            else:
                retriever_fallback = retriever_fallback or "zvec_no_hits"

        # An older index may never have indexed archived sessions. Supplement
        # auto retrieval so opting in does not depend on an index rebuild.
        if all_candidates and args.retriever == "auto" and args.archived and "codex" in runtimes_to_scan:
            known = {c["path"] for c in all_candidates}
            archived_candidates = []
            for src_dir in source_dirs:
                for c in find_codex_candidates(src_dir, None, include_archived=True):
                    if c["path"] not in known and is_archived_codex_path(c["path"]):
                        c.update(runtime="codex", source_cwd=src_dir)
                        archived_candidates.append(c)
                        known.add(c["path"])
            rank_keyword_candidates(archived_candidates, args.focus)
            for c in archived_candidates:
                if c["focus_score"] > 0:
                    all_candidates.append(c)
                    retriever_used = "zvec+keyword"

        if not all_candidates:
            # Scan every dir × runtime combination using the legacy keyword/mtime retriever.
            retriever_used = "keyword"
            for src_dir in source_dirs:
                for rt in runtimes_to_scan:
                    try:
                        kwargs = {"include_archived": args.archived} if rt == "codex" else {}
                        rt_candidates = candidate_finders[rt](src_dir, None, **kwargs)
                        for c in rt_candidates:
                            c["runtime"] = rt
                            c["source_cwd"] = src_dir
                        all_candidates.extend(rt_candidates)
                    except Exception:
                        continue

        keyword_status = None
        if args.focus and retriever_used == "keyword" and all_candidates:
            keyword_status = rank_keyword_candidates(all_candidates, args.focus)

        semantic_status = None
        if args.focus and args.retriever == "auto" and not legacy_auto and all_candidates:
            # The worker is isolated so a model crash or timeout cannot break handoff.
            request = {"focus": args.focus, "candidates": [
                {"path": str(c["path"]), "runtime": c["runtime"], "mtime": c.get("mtime", 0)}
                for c in all_candidates
            ]}
            try:
                worker = subprocess.run(
                    [sys.executable, str(Path(__file__).with_name("semantic_index.py"))],
                    input=json.dumps(request), capture_output=True, text=True, timeout=60, check=True,
                )
                semantic_status = json.loads(worker.stdout)
                by_path = {str(c["path"]): c for c in all_candidates}
                valid_hits = []
                stale_hits = 0
                lexical_hits = any(c.get("focus_score", 0) > 0 for c in all_candidates)
                for hit in semantic_status.get("matches", []):
                    c = by_path.get(hit["path"])
                    if c is None:
                        continue
                    if hit.get("source_stamp") and _session_stamp(c["path"]) != hit["source_stamp"]:
                        stale_hits += 1
                        continue
                    valid_hits.append(hit)
                    c["semantic_source_stamp"] = hit.get("source_stamp")
                    c["semantic_score"] = hit["score"]
                    c["semantic_ordinal"] = hit["ordinal"]
                    c["semantic_offset"] = hit.get("offset")
                    c["semantic_unverified"] = True
                    # A candidate, not proof of relevance; source is parsed below.
                    if not lexical_hits:
                        c["focus_score"] = 1
                semantic_status["matches"] = valid_hits
                if stale_hits:
                    semantic_status["stale_hits"] = stale_hits
                    retriever_fallback = "semantic_source_changed"
                if valid_hits:
                    retriever_used = "semantic+keyword"
            except (OSError, subprocess.SubprocessError, ValueError, KeyError) as exc:
                retriever_fallback = "semantic_error:" + type(exc).__name__
                semantic_status = {"error": retriever_fallback}

        if not all_candidates:
            rt_list = ",".join(runtimes_to_scan)
            dir_list = ",".join(source_dirs)
            print(f"No session found for source={rt_list} dirs={dir_list} focus={args.focus or ''}; {archive_scope}", file=sys.stderr)
            return 1

        # With focus active, rank by focus score first; otherwise recency wins.
        if args.focus:
            all_candidates.sort(key=lambda c: (c.get("focus_score", 0), c.get("keyword_context_matches", 0), c.get("mtime", 0)), reverse=True)
        else:
            all_candidates.sort(key=lambda c: c.get("mtime", 0), reverse=True)
        candidates = all_candidates

        # When focus is active, extract from ALL sessions with non-zero focus score.
        # Do not silently fall back to recent sessions: that creates noisy handoffs
        # and violates the Passdown contract.
        total_candidates = len(candidates)
        if args.focus:
            matched = [c for c in candidates if c.get("focus_score", 0) > 0]
            if not matched:
                rt_list = ",".join(runtimes_to_scan)
                dir_list = ",".join(source_dirs)
                print(
                    f"No session found matching focus for source={rt_list} dirs={dir_list} focus={args.focus}; {archive_scope}",
                    file=sys.stderr,
                )
                return 1
            session_paths = [c["path"] for c in matched]
            multi_session = len(session_paths) > 1
        else:
            session_paths = [candidates[0]["path"]]
            matched = [candidates[0]]

        session_path = session_paths[0]

    # Extract from all matched sessions
    all_turns = []
    automation_contexts = []
    modes = set()
    total_lines = 0
    for sp in session_paths:
        # Look up parser per session. Multi-runtime --former values still need
        # per-candidate runtime dispatch.
        rt = resolved_source
        for m in matched:
            if m.get("path") == sp:
                rt = m.get("runtime", rt)
                break
        if isinstance(rt, str) and "," in rt:
            rt = rt.split(",", 1)[0].strip()
        result = parsers.get(rt, parsers["claude"])(sp)
        smtime = _mtime(sp)
        session_turns = []
        for idx, t in enumerate(result["turns"]):
            info = automation_context(t)
            if info:
                automation_contexts.append({"session_file": str(sp), "source_ordinal": idx, **info})
            t["session_file"] = str(sp)
            t["session_mtime"] = smtime
            t["session_ordinal"] = idx
            semantic_match = next((m for m in matched if m.get("path") == sp and m.get("semantic_ordinal") == idx), None)
            if semantic_match and (not semantic_match.get("semantic_source_stamp") or
                                   _session_stamp(sp) == semantic_match["semantic_source_stamp"]):
                t["semantic_hit"] = True
                if isinstance(semantic_match.get("semantic_offset"), int):
                    t["semantic_offset"] = semantic_match["semantic_offset"]
            elif semantic_match:
                retriever_fallback = "semantic_source_changed"
                if isinstance(semantic_status, dict):
                    semantic_status["matches"] = [hit for hit in semantic_status.get("matches", [])
                                                  if hit.get("path") != str(sp)]
                    semantic_status["stale_hits"] = semantic_status.get("stale_hits", 0) + 1
            if any(m.get("path") == sp and idx in m.get("keyword_ordinals", []) for m in matched):
                t["keyword_hit"] = True
            session_turns.append(t)
        all_turns.extend(session_turns)
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

    turns, budget_stats = budget_turns(turns, args.focus, args.max_tokens)
    for context in automation_contexts:
        selected = next((t for t in turns if t.get("session_file") == context["session_file"]
                         and t.get("session_ordinal") == context["source_ordinal"]), None)
        context["instruction_status"] = ("omitted" if selected is None else
                                         "truncated" if selected.get("text_truncated") else "complete")
    total_words = sum(len(t["text"].split()) for t in turns)
    total_tokens = sum(estimate_tokens(t["text"]) for t in turns)

    # Record which runtimes contributed
    contributing_runtimes = sorted(set(
        [m.get("runtime", resolved_source) for m in matched]
    ))

    output = {
        "source": resolved_source,
        "contributing_runtimes": contributing_runtimes,
        "current_cwd": str(Path.cwd().resolve()),
        "source_cwds": source_dirs if not (args.file or args.session) else [],
        "source_cwd": ", ".join(source_dirs) if not (args.file or args.session) else str(session_path),
        "focus": args.focus,
        "retriever": retriever_used,
        "semantic_status": locals().get("semantic_status"),
        "automation_contexts": automation_contexts,
        "keyword_status": locals().get("keyword_status"),
        "include_archived": bool(args.archived or args.session or args.file),
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
        "budget": budget_stats,
        "turns": turns,
    }

    if retriever_fallback:
        output["retriever_fallback"] = retriever_fallback

    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"source:       {output['source']}")
        print(f"current cwd:  {output['current_cwd']}")
        if len(output.get('source_cwds', [])) > 1:
            print(f"source dirs:  {len(output['source_cwds'])} directories")
            for d in output['source_cwds']:
                print(f"  - {d}")
        else:
            print(f"source cwd:   {output['source_cwd'] or '-'}")
        print(f"focus:        {output['focus'] or '-'}")
        if output.get("keyword_status"):
            print(f"keyword:      {output['keyword_status']}")
        if output.get("automation_contexts"):
            print(f"automations:  {output['automation_contexts']}")
        if output.get("semantic_status"):
            print(f"semantic:     {output['semantic_status']} (candidates require source review)")
        if output['multi_session']:
            print(f"matched:      {output['matched_sessions']} sessions (focus hit)")
            for sf in output['session_files']:
                print(f"  - {sf}")
        else:
            print(f"session:      {output['session_file']}")
        print(f"candidates:   {output['candidate_count']}")
        print(f"mode:         {output['mode']}")
        print(f"lines:        {output['total_lines']}")
        print(f"turns:        {output['extracted_turns']} / {budget_stats['source_turns']} source")
        print(f"words:        ~{output['estimated_words']}")
        print(f"tokens:       ~{output['estimated_tokens']} / {budget_stats['source_estimated_tokens']} source")
        if budget_stats["budget_applied"]:
            print(
                f"budget:       {budget_stats['max_tokens']} tokens "
                f"({budget_stats['dropped_turns']} turns dropped, "
                f"{budget_stats['truncated_turns']} clipped)"
            )
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
