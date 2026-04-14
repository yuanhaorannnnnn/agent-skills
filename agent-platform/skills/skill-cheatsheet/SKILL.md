---
name: skill-cheatsheet
description: "生成 Skills 速查表。自动扫描所有已安装的 skills（官方 marketplace + 用户自定义），生成 Anthropic 品牌风格的 HTML 速查表。包含每个 skill 的名称、描述、触发词和分类。触发词：生成技能速查表、更新 cheatsheet、skills 列表、查看已安装技能、刷新技能表。"
---

# Skills 速查表生成器

自动生成所有已安装 Claude Code skills 的可视化速查表。

## 快速使用

运行脚本生成速查表：

```python
from scripts.generate_cheatsheet import generate

# 生成到默认位置 ~/.claude/skills/skills-cheatsheet.html
generate()
```

命令行：

```bash
python scripts/generate_cheatsheet.py
```

## 功能特性

- 自动扫描所有 skills 目录
- 解析 SKILL.md 获取元数据
- 生成 Anthropic 品牌风格 HTML
- 支持中文/英文切换
- 自动打开浏览器预览

## 输出位置

默认: `~/.claude/skills/skills-cheatsheet.html`

## 脚本说明

运行 `scripts/generate_cheatsheet.py` 重新生成速查表。
