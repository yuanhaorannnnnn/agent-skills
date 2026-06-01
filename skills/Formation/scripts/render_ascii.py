#!/usr/bin/env python3
"""Render a JSON topology as ASCII box-drawing art."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def box_width(text: str, min_w: int = 16) -> int:
    """Calculate box width, respecting CJK double-width characters."""
    # Simple heuristic: count characters, CJK chars count as 2
    width = 0
    for ch in text:
        if "一" <= ch <= "鿿":
            width += 2
        else:
            width += 1
    return max(width + 4, min_w)


def make_box(text: str, width: int) -> list[str]:
    """Create a box-drawing box around text with fixed width."""
    pad = width - 2  # inner width
    # Center the text
    text_width = sum(2 if "一" <= ch <= "鿿" else 1 for ch in text)
    left_pad = (pad - text_width) // 2
    right_pad = pad - text_width - left_pad
    line = "│" + " " * left_pad + text + " " * right_pad + "│"
    top = "┌" + "─" * pad + "┐"
    bottom = "└" + "─" * pad + "┘"
    return [top, line, bottom]


def render_workflow(topology: dict) -> str:
    """Render workflow topology as horizontal ASCII chain."""
    nodes = topology.get("nodes", [])
    edges = topology.get("edges", [])

    if not nodes:
        return "(no nodes)"

    # Build adjacency list
    adj: dict[str, list[tuple[str, str]]] = {}
    for edge in edges:
        src = edge.get("from", "")
        dst = edge.get("to", "")
        label = edge.get("label", "")
        adj.setdefault(src, []).append((dst, label))

    # Find root nodes (no incoming edges)
    all_targets = {e.get("to", "") for e in edges}
    roots = [n["id"] for n in nodes if n["id"] not in all_targets]

    # If no roots, use first node
    if not roots:
        roots = [nodes[0]["id"]]

    # Build node name map
    name_map = {n["id"]: n.get("name", n["id"]) for n in nodes}

    # Simple approach: linear chain from first root, follow edges depth-first
    visited = set()
    order: list[str] = []

    def dfs(node_id: str) -> None:
        if node_id in visited:
            return
        visited.add(node_id)
        order.append(node_id)
        for dst, _ in adj.get(node_id, []):
            dfs(dst)

    for root in roots:
        dfs(root)

    # Add any unvisited nodes at the end
    for n in nodes:
        if n["id"] not in visited:
            order.append(n["id"])

    # Build ASCII chain
    if len(order) == 1:
        box = make_box(name_map[order[0]], box_width(name_map[order[0]]))
        return "\n".join(box)

    # Multi-node
    boxes = []
    for node_id in order:
        name = name_map.get(node_id, node_id)
        bw = box_width(name)
        box = make_box(name, bw)
        boxes.append(box)

    lines = []

    # If no edges, render as isolated boxes (no fake arrows)
    if not edges:
        top_parts = [b[0] for b in boxes]
        mid_parts = [b[1] for b in boxes]
        bot_parts = [b[2] for b in boxes]
        lines.append("  ".join(top_parts))
        lines.append("  ".join(mid_parts))
        lines.append("  ".join(bot_parts))
        return "\n".join(lines)

    # With edges: draw horizontal chain with arrows
    top_parts = []
    for box in boxes:
        top_parts.append(box[0])
    lines.append("  ".join(top_parts))

    mid_parts = []
    for i, box in enumerate(boxes):
        mid_parts.append(box[1])
        if i < len(boxes) - 1:
            mid_parts.append("──▶")
    lines.append("  ".join(mid_parts))

    bot_parts = []
    for box in boxes:
        bot_parts.append(box[2])
    lines.append("  ".join(bot_parts))

    return "\n".join(lines)


def render_architecture(topology: dict) -> str:
    """Render architecture topology as layered ASCII."""
    nodes = topology.get("nodes", [])
    edges = topology.get("edges", [])
    groups = topology.get("groups", [])

    if not nodes:
        return "(no nodes)"

    name_map = {n["id"]: n.get("name", n["id"]) for n in nodes}

    # If no groups, create a single default group
    if not groups:
        groups = [{"name": "Skills", "members": [n["id"] for n in nodes]}]

    # Build group boxes
    lines = []
    for group in groups:
        g_name = group.get("name", "")
        members = group.get("members", [])

        # Group header
        lines.append(f"  [{g_name}]")

        # Member boxes in a row
        boxes = []
        for m in members:
            name = name_map.get(m, m)
            bw = box_width(name)
            boxes.append(make_box(name, bw))

        if boxes:
            # Top
            top_parts = [b[0] for b in boxes]
            lines.append("    " + "  ".join(top_parts))
            # Middle
            mid_parts = [b[1] for b in boxes]
            lines.append("    " + "  ".join(mid_parts))
            # Bottom
            bot_parts = [b[2] for b in boxes]
            lines.append("    " + "  ".join(bot_parts))

        # Vertical separator between groups
        lines.append("")

    # Add cross-group edges as annotations
    if edges:
        lines.append("  Connections:")
        for edge in edges:
            src = name_map.get(edge.get("from", ""), edge.get("from", ""))
            dst = name_map.get(edge.get("to", ""), edge.get("to", ""))
            label = edge.get("label", "")
            if label:
                lines.append(f"    {src} ──▶ {dst}  ({label})")
            else:
                lines.append(f"    {src} ──▶ {dst}")

    return "\n".join(lines)


def render(topology: dict, mold: str) -> str:
    """Render topology as ASCII art based on mold type."""
    if mold == "workflow":
        return render_workflow(topology)
    elif mold == "architecture":
        return render_architecture(topology)
    else:
        return f"Unknown mold: {mold}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render a JSON topology as ASCII box-drawing art."
    )
    parser.add_argument("topology", help="Path to JSON topology file")
    parser.add_argument(
        "--mold",
        choices=["workflow", "architecture"],
        default="workflow",
        help="Mold type (default: workflow)",
    )
    args = parser.parse_args()

    path = Path(args.topology)
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        return 1

    topology = json.loads(path.read_text(encoding="utf-8"))
    print(render(topology, args.mold))
    return 0


if __name__ == "__main__":
    sys.exit(main())
