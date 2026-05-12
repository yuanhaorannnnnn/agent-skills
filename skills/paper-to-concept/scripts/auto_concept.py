#!/usr/bin/env python3
"""
auto_concept.py: 自动将论文笔记整理到 wiki concept 页

输入：论文笔记文件路径（~/Documents/notes/YYYYMMDDTHHMMSS--paper-{标题}__paper.md）
输出：更新的 concept 页路径列表
"""

import re
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Wiki 根目录
WIKI_ROOT = Path("/media/yhr/2T/files/wiki")
NOTES_DIR = Path.home() / "Documents" / "notes"
CONCEPTS_DIR = WIKI_ROOT / "concepts"
ENTITIES_DIR = WIKI_ROOT / "entities"
INDEX_FILE = WIKI_ROOT / "index.md"
LOG_FILE = WIKI_ROOT / "log.md"


def parse_paper_note(note_path: Path) -> dict:
    """解析论文笔记，提取 frontmatter 和关键信息。"""
    content = note_path.read_text(encoding="utf-8")
    
    # 提取 YAML frontmatter
    fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    frontmatter = {}
    if fm_match:
        import yaml
        frontmatter = yaml.safe_load(fm_match.group(1))
    
    # 提取正文中的关键信息
    sections = {}
    current_section = None
    for line in content.split('\n'):
        if line.startswith('# ') and not line.startswith('## '):
            current_section = line[2:].strip().lower().replace(' ', '_')
            sections[current_section] = []
        elif current_section and line.strip():
            sections[current_section].append(line)
    
    return {
        "path": str(note_path),
        "filename": note_path.name,
        "frontmatter": frontmatter,
        "sections": sections,
        "content": content,
    }


def get_existing_concepts() -> list:
    """获取现有 concept 列表。"""
    if not CONCEPTS_DIR.exists():
        return []
    return [f.stem for f in CONCEPTS_DIR.glob("*.md")]


def classify_concepts(paper_info: dict, existing_concepts: list) -> dict:
    """
    用 LLM 判断论文归属哪些 concept。
    这里返回一个模拟结果，实际应由 LLM 调用填充。
    """
    # TODO: 这里应该调用 LLM 进行分类
    # 返回格式：
    # {
    #   "existing": ["concept1", "concept2"],  # 归属的现有 concept
    #   "new": [{"name": "new-concept", "description": "..."}],  # 需要新建的
    # }
    return {
        "existing": [],
        "new": [],
        "reasoning": "待 LLM 分类",
    }


def update_concept(concept_name: str, paper_info: dict, is_new: bool = False) -> Path:
    """更新或创建 concept 页。"""
    concept_path = CONCEPTS_DIR / f"{concept_name}.md"
    today = datetime.now().strftime("%Y-%m-%d")
    
    if is_new:
        # 创建新 concept
        fm = paper_info["frontmatter"]
        content = f"""---
title: "{concept_name.replace('-', ' ').title()}"
created: {today}
updated: {today}
type: concept
tags: [concept]
papers:
  - {paper_info["filename"]}
---

# {concept_name.replace('-', ' ').title()}

## 概述
{{待补充：基于论文笔记生成通用概述}}

## 核心问题
{{待补充：从论文中提取的共性问题}}

## 技术演进
{{待补充：跨论文的时序排序，每篇论文一行摘要}}

## 关键概念
{{待补充：通用概念}}

## 洞见
{{待补充：思想结晶}}

## 相关论文
- [[{paper_info["filename"]}]]
"""
        concept_path.write_text(content, encoding="utf-8")
    else:
        # 更新现有 concept
        existing = concept_path.read_text(encoding="utf-8")
        # 更新 frontmatter 的 papers 列表和 updated
        # 在 "相关论文" 部分添加新论文
        if paper_info["filename"] not in existing:
            # 简单追加到相关论文部分
            existing = existing.replace(
                "## 相关论文",
                f"## 相关论文\n- [[{paper_info['filename']}]]"
            )
            # 更新 updated
            existing = re.sub(
                r'updated: \d{4}-\d{2}-\d{2}',
                f'updated: {today}',
                existing
            )
            concept_path.write_text(existing, encoding="utf-8")
    
    return concept_path


def update_index(concept_names: list, paper_info: dict):
    """更新 index.md。"""
    if not INDEX_FILE.exists():
        return
    
    index_content = INDEX_FILE.read_text(encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 更新 Last updated
    index_content = re.sub(
        r'Last updated: .*',
        f'Last updated: {today}',
        index_content
    )
    
    # 更新 Total pages（简单计数）
    total = len(list(WIKI_ROOT.rglob("*.md")))
    index_content = re.sub(
        r'Total pages: \d+',
        f'Total pages: {total}',
        index_content
    )
    
    # 在 Concepts 区添加新条目（如果不存在）
    for concept in concept_names:
        if concept not in index_content:
            # 找到 Concepts 区，追加
            index_content = index_content.replace(
                "## Concepts",
                f"## Concepts\n- [[{concept}]]"
            )
    
    INDEX_FILE.write_text(index_content, encoding="utf-8")


def update_log(paper_info: dict, concept_names: list):
    """更新 log.md。"""
    today = datetime.now().strftime("%Y-%m-%d")
    fm = paper_info["frontmatter"]
    title = fm.get("title", "Unknown")
    
    log_entry = f"\n## [{today}] paper-to-concept | {title} → {', '.join(concept_names)}\n"
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)


def update_entities(paper_info: dict):
    """更新 entities（作者、机构、venue）。"""
    fm = paper_info["frontmatter"]
    authors = fm.get("authors", "")
    venue = fm.get("venue", "")
    
    # 处理作者
    if authors:
        # 支持字符串逗号分隔和列表两种格式
        if isinstance(authors, str):
            author_list = [a.strip() for a in authors.split(",")]
        elif isinstance(authors, (list, tuple)):
            author_list = [str(a).strip() for a in authors]
        else:
            author_list = []
        
        for author in author_list:
            if not author:
                continue
            # 清理非法文件名字符
            safe_name = re.sub(r'[^a-z0-9\-\.]', '-', author.lower().replace(" ", "-")).strip('-')
            entity_path = ENTITIES_DIR / f"{safe_name}.md"
            
            if not entity_path.exists():
                today = datetime.now().strftime("%Y-%m-%d")
                content = f"""---
title: {author}
created: {today}
updated: {today}
type: entity
subtype: author
papers:
  - {paper_info["filename"]}
---
"""
                entity_path.write_text(content, encoding="utf-8")
    
    # 处理 venue
    if venue:
        # 清理非法文件名字符
        safe_name = re.sub(r'[^a-z0-9\-\.]', '-', venue.lower().replace(" ", "-")).strip('-')
        entity_path = ENTITIES_DIR / f"{safe_name}.md"
        
        if not entity_path.exists():
            today = datetime.now().strftime("%Y-%m-%d")
            content = f"""---
title: {venue}
created: {today}
updated: {today}
type: entity
subtype: venue
papers:
  - {paper_info["filename"]}
---
"""
            entity_path.write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Auto-concept paper note")
    parser.add_argument("note_path", help="Path to paper note (__paper.md)")
    parser.add_argument("--concepts", help="JSON array of concept names to assign")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()
    
    note_path = Path(args.note_path)
    if not note_path.exists():
        print(f"Error: Note not found: {note_path}")
        sys.exit(1)
    
    # 解析论文笔记
    paper_info = parse_paper_note(note_path)
    print(f"Parsed paper: {paper_info['frontmatter'].get('title', 'Unknown')}")
    
    # 获取现有 concept
    existing = get_existing_concepts()
    print(f"Existing concepts: {existing}")
    
    # 分类（如果命令行提供了 concept 列表，直接使用；否则需要 LLM 分类）
    if args.concepts:
        concept_names = json.loads(args.concepts)
    else:
        # 这里应该调用 LLM，但脚本层面只能做占位
        # 实际使用时，由 wrapper skill 调用 LLM 后传入 --concepts
        print("Warning: No concepts provided. Use --concepts '[\"name1\", \"name2\"]'")
        concept_names = []
    
    if args.dry_run:
        print(f"Would update concepts: {concept_names}")
        print(f"Would update index.md and log.md")
        return
    
    # 更新 concept 页
    updated_concepts = []
    for concept in concept_names:
        is_new = concept not in existing
        path = update_concept(concept, paper_info, is_new)
        updated_concepts.append(str(path))
        print(f"{'Created' if is_new else 'Updated'} concept: {path}")
    
    # 更新 index 和 log
    update_index(concept_names, paper_info)
    update_log(paper_info, concept_names)
    
    # 更新 entities
    update_entities(paper_info)
    
    print(f"\nDone! Updated {len(updated_concepts)} concepts.")
    print(f"Wiki root: {WIKI_ROOT}")


if __name__ == "__main__":
    main()
