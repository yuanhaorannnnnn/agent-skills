#!/usr/bin/env python3
"""Build and inspect the local zvec index used by Passdown.

zvec is a candidate retriever only. The extractor still re-reads the original
JSONL session files and owns all parsing, filtering, compression, and output.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import extract_handoff as eh  # noqa: E402

INSERT_BATCH_SIZE = 512
MIN_CHUNK_CHARS = 30


def parse_csv(values: list[str] | None, default: list[str]) -> list[str]:
    if not values:
        return default
    out: list[str] = []
    for value in values:
        for part in value.split(','):
            part = part.strip()
            if part and part not in out:
                out.append(part)
    return out or default


def source_dirs_from_args(args) -> list[str]:
    dirs = parse_csv((args.source_dir or []) + (args.cwd or []), [os.getcwd()])
    return [str(Path(d).expanduser().resolve()) for d in dirs]


def runtimes_from_args(args) -> list[str]:
    return parse_csv(args.former or args.source, ["codex", "pi", "claude"])


def open_collection(create: bool = False):
    try:
        import zvec  # type: ignore
    except Exception as exc:
        raise RuntimeError("zvec is not installed in this Python environment") from exc
    schema = zvec.CollectionSchema(
        name="passdown_sessions",
        vectors=zvec.VectorSchema("text_embedding", zvec.DataType.VECTOR_FP32, eh.EMBEDDING_DIM),
    )
    index_path = eh.passdown_zvec_path()
    if create:
        return zvec.create_and_open(path=str(index_path), schema=schema)
    return zvec.open(path=str(index_path))


def discover_sessions(source_dirs: list[str], runtimes: list[str]) -> list[dict]:
    candidate_finders = {
        "codex": eh.find_codex_candidates,
        "pi": eh.find_pi_candidates,
        "claude": eh.find_claude_candidates,
    }
    seen: set[tuple[str, str, str]] = set()
    sessions: list[dict] = []
    for source_cwd in source_dirs:
        for runtime in runtimes:
            finder = candidate_finders.get(runtime)
            if not finder:
                continue
            for candidate in finder(source_cwd, None):
                path = Path(candidate["path"])
                key = (str(path), runtime, source_cwd)
                if key in seen:
                    continue
                seen.add(key)
                sessions.append({
                    "path": path,
                    "runtime": runtime,
                    "source_cwd": source_cwd,
                    "mtime": eh._mtime(path),
                })
    sessions.sort(key=lambda item: item["mtime"])
    return sessions


def build_index(args) -> int:
    source_dirs = source_dirs_from_args(args)
    runtimes = runtimes_from_args(args)
    sessions = discover_sessions(source_dirs, runtimes)
    if args.dry_run:
        print(json.dumps({
            "index_path": str(eh.passdown_zvec_path()),
            "source_dirs": source_dirs,
            "runtimes": runtimes,
            "session_files": len(sessions),
        }, ensure_ascii=False, indent=2))
        return 0

    try:
        import zvec  # type: ignore
    except Exception as exc:
        print(f"Error: zvec is not installed: {exc}", file=sys.stderr)
        return 1

    index_path = eh.passdown_zvec_path()
    if args.rebuild and index_path.exists():
        shutil.rmtree(index_path)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    collection = open_collection(create=not index_path.exists())

    parsers = {"codex": eh.parse_codex, "pi": eh.parse_pi, "claude": eh.parse_claude}
    sidecar = index_path / "metadata.jsonl"
    total_chunks = 0
    skipped_files = 0
    runtime_counts: Counter[str] = Counter()
    with sidecar.open("w", encoding="utf-8") as meta_f:
        for session in sessions:
            path = session["path"]
            runtime = session["runtime"]
            parser = parsers[runtime]
            try:
                result = parser(path)
            except Exception as exc:
                skipped_files += 1
                if args.verbose:
                    print(f"skip {runtime}:{path}: {exc}", file=sys.stderr)
                continue
            docs = []
            session_mtime = eh._mtime(path)
            fhash = eh.hashlib.sha256(f"{runtime}:{path}".encode()).hexdigest()[:16]
            chunk_index = 0
            for turn_index, turn in enumerate(result.get("turns", [])):
                text = (turn.get("text") or "").strip()
                if len(text) < MIN_CHUNK_CHARS:
                    continue
                doc_id = f"{runtime}_{fhash}_{chunk_index}"
                docs.append(zvec.Doc(id=doc_id, vectors={"text_embedding": eh.embed_text(text)}))
                meta_f.write(json.dumps({
                    "id": doc_id,
                    "session_file": str(path),
                    "session_mtime": session_mtime,
                    "runtime": runtime,
                    "source_cwd": session["source_cwd"],
                    "role": turn.get("role", ""),
                    "turn_index": turn_index,
                    "text_preview": text[:240],
                    "text_len": len(text),
                }, ensure_ascii=False, separators=(",", ":")) + "\n")
                chunk_index += 1
            for start in range(0, len(docs), INSERT_BATCH_SIZE):
                collection.insert(docs[start:start + INSERT_BATCH_SIZE])
            if docs:
                total_chunks += len(docs)
                runtime_counts[runtime] += len(docs)
            else:
                skipped_files += 1
    print(json.dumps({
        "index_path": str(index_path),
        "session_files": len(sessions),
        "chunks": total_chunks,
        "skipped_files": skipped_files,
        "runtime_chunks": dict(sorted(runtime_counts.items())),
    }, ensure_ascii=False, indent=2))
    return 0


def show_stats() -> int:
    index_path = eh.passdown_zvec_path()
    sidecar = index_path / "metadata.jsonl"
    if not sidecar.exists():
        print(json.dumps({"index_path": str(index_path), "exists": index_path.exists(), "chunks": 0}, indent=2))
        return 1
    runtime_counts: Counter[str] = Counter()
    session_files: set[str] = set()
    chunks = 0
    with sidecar.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                meta = json.loads(line)
            except json.JSONDecodeError:
                continue
            chunks += 1
            runtime_counts[meta.get("runtime", "unknown")] += 1
            if meta.get("session_file"):
                session_files.add(meta["session_file"])
    print(json.dumps({
        "index_path": str(index_path),
        "exists": index_path.exists(),
        "session_files": len(session_files),
        "chunks": chunks,
        "runtime_chunks": dict(sorted(runtime_counts.items())),
    }, ensure_ascii=False, indent=2))
    return 0


def query_index(args) -> int:
    source_dirs = source_dirs_from_args(args)
    runtimes = runtimes_from_args(args)
    candidates = eh.find_zvec_candidates(source_dirs, runtimes, args.focus, top_k=args.top_k, min_sessions=args.min_sessions)
    payload = [{k: (str(v) if isinstance(v, Path) else v) for k, v in c.items()} for c in candidates]
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Build/query Passdown zvec candidate index")
    parser.add_argument("--former", action="append", help="Source agent(s): codex,pi,claude. Repeatable/comma-separated.")
    parser.add_argument("--source", action="append", help="Alias for --former")
    parser.add_argument("--cwd", action="append", help="Source working directory. Repeatable/comma-separated.")
    parser.add_argument("--dir", dest="source_dir", action="append", help="Alias for --cwd")
    parser.add_argument("--rebuild", action="store_true", help="Delete and rebuild the zvec index")
    parser.add_argument("--dry-run", action="store_true", help="Only report discovered sessions")
    parser.add_argument("--stats", action="store_true", help="Show sidecar metadata stats")
    parser.add_argument("--focus", help="Query focus text")
    parser.add_argument("--top-k", type=int, default=80)
    parser.add_argument("--min-sessions", type=int, default=20)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.stats:
        return show_stats()
    if args.focus:
        return query_index(args)
    return build_index(args)


if __name__ == "__main__":
    raise SystemExit(main())
