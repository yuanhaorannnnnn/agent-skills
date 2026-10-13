#!/usr/bin/env python3
"""Search curated historical artifacts in Canon's artifact-index."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_INDEX = Path("/media/yhr/2T/Canon/artifacts/artifact-index.md")
LINK_FIELDS = ("source_path", "task_path", "update_card")


def _entries(index_path: Path) -> list[dict[str, object]]:
    text = index_path.read_text(encoding="utf-8")
    fenced = re.search(r"```yaml\s*(.*?)```", text, re.DOTALL)
    if not fenced:
        raise ValueError(f"No YAML artifact registry found in {index_path}")
    entries: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for line in fenced.group(1).splitlines():
        if line.startswith("- id: "):
            if current:
                entries.append(current)
            current = {"id": line.split(":", 1)[1].strip()}
        elif current and line.startswith("  ") and not line.startswith("    ") and ": " in line:
            key, value = line.strip().split(": ", 1)
            if key in {"original_terms", "aliases"}:
                try:
                    parsed = json.loads(value)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{key} must use a JSON-compatible YAML string list") from exc
                if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
                    raise ValueError(f"{key} must be a list of strings")
                current[key] = parsed
            elif key in {"kind", "title", "source_path", "task_path", "update_card", "alias_note", "date", "status", "notes"}:
                current[key] = value.strip('"\'')
    if current:
        entries.append(current)
    return [entry for entry in entries if entry.get("kind") == "historical-summary"]


def _normalize(value: str) -> str:
    return re.sub(r"[^\w\u3400-\u9fff]", "", value.casefold(), flags=re.UNICODE)


def _mapped_path(raw_path: str, base: Path, mappings: list[str]) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = base / path
    candidates: list[tuple[int, Path, Path]] = []
    for mapping in mappings:
        if "=" not in mapping:
            raise ValueError(f"Invalid --map-prefix {mapping!r}; expected OLD=NEW")
        old, new = mapping.split("=", 1)
        old_path = Path(old)
        try:
            relative = path.relative_to(old_path)
        except ValueError:
            continue
        candidates.append((len(str(old_path)), old_path, Path(new) / relative))
    return max(candidates, default=(0, Path(), path))[2]


def _links(entry: dict[str, object], index_dir: Path, mappings: list[str]) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for field in LINK_FIELDS:
        raw = entry.get(field)
        if isinstance(raw, str) and raw:
            resolved = _mapped_path(raw, index_dir, mappings)
            result[field] = {"path": raw, "exists": resolved.is_file()}
    return result


def _score(entry: dict[str, object], query: str) -> tuple[int, list[str]]:
    needle = _normalize(query)
    if not needle:
        return 0, []
    alias_hits = [str(item) for item in entry.get("aliases", []) if _normalize(str(item)) in needle]
    term_hits = [str(item) for item in entry.get("original_terms", []) if _normalize(str(item)) in needle]
    # Long aliases are intentional recall hooks; generic one-token overlap is not enough.
    return 3 * len(alias_hits) + 2 * len(term_hits), alias_hits + term_hits


def query(index: Path, text: str, mappings: list[str]) -> dict[str, object]:
    ranked = []
    for entry in _entries(index):
        score, matched = _score(entry, text)
        if score:
            links = _links(entry, index.parent, mappings)
            source = links.get("source_path", {})
            ranked.append({
                "id": entry["id"],
                "title": entry.get("title", entry["id"]),
                "score": score,
                "matched_terms": matched,
                "original_terms": entry.get("original_terms", []),
                "aliases": entry.get("aliases", []),
                "alias_note": entry.get("alias_note", ""),
                "date": entry.get("date"),
                "status": entry.get("status"),
                "source_path": entry.get("source_path"),
                "source_read": False,
                "source_status": "exists_not_read" if source.get("exists") else "missing",
                "links": links,
            })
    ranked.sort(key=lambda item: (-int(item["score"]), str(item["id"])))
    return {"query": text, "candidates": ranked}


def check_links(index: Path, artifact_id: str, mappings: list[str]) -> dict[str, object]:
    entry = next((item for item in _entries(index) if item.get("id") == artifact_id), None)
    if entry is None:
        raise ValueError(f"Unknown indexed artifact: {artifact_id}")
    links = _links(entry, index.parent, mappings)
    missing = [name for name, link in links.items() if not link["exists"]]
    if "source_path" not in links:
        missing.insert(0, "source_path")
    return {"id": artifact_id, "links": links, "missing": missing, "ok": not missing}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--map-prefix", action="append", default=[], metavar="OLD=NEW",
                        help="map an absolute source prefix into a fixture or mirror tree")
    sub = parser.add_subparsers(dest="command", required=True)
    search = sub.add_parser("query", help="rank historical artifact candidates")
    search.add_argument("text", nargs="+")
    links = sub.add_parser("check-links", help="inspect links for one curated entry")
    links.add_argument("id", help="historical-summary artifact id from the index")
    args = parser.parse_args()
    try:
        if args.command == "query":
            result = query(args.index, " ".join(args.text), args.map_prefix)
        else:
            result = check_links(args.index, args.id, args.map_prefix)
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if args.command == "check-links" and not result["ok"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
