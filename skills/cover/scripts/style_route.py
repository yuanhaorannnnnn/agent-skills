#!/usr/bin/env python3
"""Validate observed features and route a design brief, without claiming vision inference."""
import argparse
import json
from pathlib import Path
import sys

DEFAULT_CATALOG = Path(__file__).resolve().parents[1] / "references/style-catalog.json"
MEDIA = {"page", "image", "video"}
LEVELS = {"frames", "sequence", "audio"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def strings(value):
    return isinstance(value, list) and all(isinstance(x, str) and x.strip() for x in value)


def normalize(value):
    return " ".join(value.casefold().strip().split())


def validate_catalog(catalog):
    require(catalog.get("schema_version") == 1, "unsupported catalog schema_version")
    features = catalog.get("features")
    require(isinstance(features, dict) and features, "features must be a nonempty object")
    for key, feature in features.items():
        require(isinstance(feature, dict), f"invalid feature: {key}")
        require(feature.get("dimension") and feature.get("description"), f"incomplete feature: {key}")
        require(feature.get("required_level") in LEVELS, f"invalid evidence level: {key}")
    styles = catalog.get("styles")
    require(isinstance(styles, list) and styles, "styles must be a nonempty list")
    aliases = {}
    for style in styles:
        require(isinstance(style, dict), "invalid style")
        sid = style.get("id")
        require(isinstance(sid, str) and sid.strip(), "style id required")
        require(strings(style.get("aliases")), f"aliases required: {sid}")
        for alias in [sid] + style["aliases"]:
            token = normalize(alias)
            require(token not in aliases or aliases[token] == sid, f"ambiguous alias: {alias}")
            aliases[token] = sid
        signatures = style.get("signature_features")
        require(strings(signatures) and len(set(signatures)) >= 2, f"need multiple signatures: {sid}")
        require(all(f in features for f in signatures), f"unknown signature: {sid}")
        require(len({features[f]["dimension"] for f in signatures}) >= 2, f"need multiple dimensions: {sid}")
        require(isinstance(style.get("media"), dict) and style["media"], f"media required: {sid}")
        require(set(style["media"]) <= MEDIA, f"unknown medium: {sid}")
        require(all(isinstance(v, str) and v.strip() for v in style["media"].values()), f"empty medium rule: {sid}")
        require(style.get("thesis") and style.get("distinguish"), f"missing interpretation: {sid}")
        require(isinstance(style.get("auto_match", True), bool), f"auto_match must be boolean: {sid}")
        if not style.get("auto_match", True):
            require(isinstance(style.get("refinement"), str) and style["refinement"].strip(), f"refinement required: {sid}")
        if "source_label" in style:
            require(isinstance(style.get("historical_scope"), str) and style["historical_scope"].strip(), f"historical scope required: {sid}")
            sources = style.get("sources")
            require(isinstance(sources, list) and sources, f"sources required: {sid}")
            require(all(isinstance(source, dict) and isinstance(source.get("url"), str)
                        and source["url"].startswith("https://") and source.get("title") for source in sources),
                    f"invalid source reference: {sid}")
    require(len({s["id"] for s in styles}) == len(styles), "duplicate style id")
    return aliases


def validate_observations(observations, catalog):
    require(isinstance(observations, list), "observations must be a list")
    for observation in observations:
        require(isinstance(observation, dict), "observation must be an object")
        feature = observation.get("feature")
        require(feature in catalog["features"], f"unknown observed feature: {feature}")
        for field in ("source", "scope", "locator", "note"):
            require(isinstance(observation.get(field), str) and observation[field].strip(), f"observation {field} required")
        level = observation.get("level")
        needed = catalog["features"][feature]["required_level"]
        require(level == needed or (needed == "frames" and level == "sequence"),
                f"{feature} requires {needed} evidence, got {level}")


def validate_references(document, catalog):
    refs = document.get("references", [])
    require(isinstance(refs, list), "references must be a list")
    seen = set()
    for ref in refs:
        require(isinstance(ref, dict) and isinstance(ref.get("id"), str), "reference id required")
        require(ref["id"] not in seen, "duplicate reference id")
        seen.add(ref["id"])
        require(isinstance(ref.get("source_url"), str) and ref["source_url"].strip(), "reference source_url required")
        # Existing raw manifests remain valid; unannotated refs provide no style evidence.
        validate_observations(ref.get("style_observations", []), catalog)
        sources = {ref["source_url"]} | {ref[k] for k in ("archive", "contact_sheet") if isinstance(ref.get(k), str)}
        require(all(o["source"] in sources for o in ref.get("style_observations", [])),
                f"observation source does not belong to reference: {ref['id']}")
    return {ref["id"]: ref for ref in refs}


def route(brief, catalog, references=None):
    require(isinstance(brief, dict), "brief must be an object")
    aliases = validate_catalog(catalog)
    refs = validate_references(references or {}, catalog)
    allowed = {"medium", "explicit_style", "project", "exclude_styles", "observations", "reference_ids"}
    require(set(brief) <= allowed, f"unknown brief fields: {sorted(set(brief) - allowed)}")
    medium = brief.get("medium")
    require(medium in MEDIA, "medium must be page, image or video")
    observations = list(brief.get("observations", []))
    validate_observations(observations, catalog)
    requested_refs = brief.get("reference_ids", [])
    require(strings(requested_refs), "reference_ids must be strings")
    for rid in requested_refs:
        require(rid in refs, f"unknown reference id: {rid}")
        observations.extend(refs[rid].get("style_observations", []))
    exclusions = brief.get("exclude_styles", [])
    require(strings(exclusions), "exclude_styles must be strings")
    for value in exclusions:
        require(normalize(value) in aliases, f"unknown exclusion: {value}")
    excluded = {aliases[normalize(x)] for x in exclusions}
    styles = {s["id"]: s for s in catalog["styles"]}
    result = {"status": None, "medium": medium, "selection_scope": "style-family",
              "artifact_direction_required": True, "selected": None, "candidates": [], "context_candidates": [],
              "reason": "", "observations": observations,
              "limits": ["Feature matching is not image recognition or aesthetic acceptance.",
                         "Palette, creator identity and topic keywords do not determine style."]}
    if medium == "video":
        result["limits"].append("Visual direction does not establish verified motion, sound or an exported film.")
    explicit = brief.get("explicit_style")
    if explicit is not None:
        require(isinstance(explicit, str) and explicit.strip(), "explicit_style must be a nonempty string")
        sid = aliases.get(normalize(explicit))
        if sid is None:
            result.update(status="needs_style_definition", reason="Explicit direction is not registered; do not substitute another style.")
            return result
        if sid in excluded or medium not in styles[sid]["media"]:
            result.update(status="conflict", reason="Explicit direction is excluded or has no rule for this medium.")
            return result
        result.update(status="selected", selected=sid, reason="Explicit user direction.",
                      medium_rule=styles[sid]["media"][medium], basis="explicit",
                      reference_refinement_required=not styles[sid].get("auto_match", True),
                      refinement=styles[sid].get("refinement"), sources=styles[sid].get("sources", []),
                      historical_scope=styles[sid].get("historical_scope"),
                      distinguish=styles[sid]["distinguish"],
                      media_status=styles[sid].get("media_status", "project design treatment"))
        if brief.get("project"):
            result["project_override"] = "Scope this selection to the artifact; preserve the project DESIGN.md."
        return result
    project = brief.get("project")
    if project is not None:
        require(isinstance(project, dict), "project must be an object")
        sid, design = project.get("style_id"), project.get("design")
        require(isinstance(sid, str) and sid.strip() and isinstance(design, str) and design.strip(),
                "project requires style_id and absolute design path")
        require(Path(design).is_absolute() and Path(design).is_file(), "project design must be an existing absolute file")
        resolved = aliases.get(normalize(sid), sid)
        if resolved in excluded:
            result.update(status="conflict", reason="Project direction is excluded; choose a scoped override.")
        else:
            result.update(status="selected", selected=resolved, basis="project", design_source=design,
                          reason="Preserve existing project direction; caller must read its medium rules.")
            if resolved in styles:
                result["reference_refinement_required"] = not styles[resolved].get("auto_match", True)
                result["refinement"] = styles[resolved].get("refinement")
        return result
    groups = {}
    for observation in observations:
        key = (observation["source"], observation["scope"])
        groups.setdefault(key, set()).add(observation["feature"])
    for sid, style in styles.items():
        if sid in excluded or medium not in style["media"]:
            continue
        signatures = set(style["signature_features"])
        supporting = {key for key, found in groups.items() if signatures <= found}
        if supporting:
            destination = "candidates" if style.get("auto_match", True) else "context_candidates"
            result[destination].append({"id": sid, "matched_features": sorted(signatures),
                "evidence": [o for o in observations if o["feature"] in signatures and (o["source"], o["scope"]) in supporting],
                "thesis": style["thesis"], "distinguish": style["distinguish"],
                "medium_rule": style["media"][medium], "refinement": style.get("refinement"),
                "sources": style.get("sources", [])})
    count = len(result["candidates"])
    if count == 1:
        result.update(status="proposed", reason="One complete visual signature matches; review its distinction and task fit before selection.")
    elif count > 1:
        result.update(status="ambiguous", reason="Multiple signatures match. Mixed references are not a single chosen direction.")
    elif result["context_candidates"]:
        result.update(status="needs_context", reason="Visual resemblance is insufficient for these historical groups or umbrella terms. Inspect a specific work and contextual sources before choosing a branch.")
    else:
        result.update(status="needs_observation", reason="No complete signature. Inspect the work or define a new direction; no warm-paper fallback.")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--references", type=Path)
    parser.add_argument("--brief", type=Path)
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    try:
        catalog = json.loads(args.catalog.read_text())
        refs = json.loads(args.references.read_text()) if args.references else {}
        if args.validate:
            validate_catalog(catalog)
            validate_references(refs, catalog)
            result = {"status": "valid", "check_kind": "catalog_and_observation_structure"}
        else:
            require(args.brief is not None, "--brief is required unless --validate")
            result = route(json.loads(args.brief.read_text()), catalog, refs)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, AttributeError, KeyError) as error:
        print(json.dumps({"status": "error", "reason": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
