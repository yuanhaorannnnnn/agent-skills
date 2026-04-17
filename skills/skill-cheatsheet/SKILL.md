---
name: skill-cheatsheet
description: |
  生成 Coding Agent Skills 速查表。自动扫描所有已安装的 skills（通用 agent + 特定 agent runtime），
  生成 Anthropic 品牌风格的 HTML 速查表。自动识别上游仓库来源（gstack、anthropics、superpowers、
  planning-with-files、agent-skills、marketplace）。支持按功能分类和按发布商分组两种视图，
  可在页面上通过标签按钮切换。触发词：生成技能速查表、更新 cheatsheet、skills 列表、
  查看已安装技能、刷新技能表。Also use this skill when the user asks for a skills cheatsheet,
  installed skills inventory, skill catalog, or wants to browse available skills across runtimes.
---

# Skills 速查表生成器

自动生成所有已安装 coding-agent skills 的可视化速查表。

## 快速使用

运行脚本生成速查表：

```python
from scripts.generate_cheatsheet import generate

generate()
```

命令行：

```bash
python scripts/generate_cheatsheet.py
```

## 功能特性

- 自动扫描多个 skills 目录：
  - 通用 agent：`~/.agents/skills`
  - 特定 agent runtime：`~/.claude/skills`、`~/.codex/skills`、`~/.pi/agent/skills`
  - 官方 marketplace：`~/.claude/plugins/marketplaces/anthropic-agent-skills/skills`
- 解析 SKILL.md 获取元数据，支持多行 YAML frontmatter
- **自动识别上游仓库来源**：通过解析 symlink 真实路径推断所属上游；对于直接安装在 `~/.agents/skills` 下的 `impeccable` 设计技能套件，也会显式识别为 `impeccable`
- **页内视图切换**：生成的 HTML 顶部有两个标签页按钮，可在以下两种视图间切换：
  - **功能分类**：文档 / 设计 / 开发 / 沟通
  - **发布商分组**：gstack / anthropics / superpowers / **impeccable** / agent-skills / marketplace / local
- 生成 Anthropic 品牌风格 HTML
- 支持中文/英文切换
- 自动打开浏览器预览

## 输出位置

默认: `~/.agents/skills/skills-cheatsheet.html`

## 脚本说明

运行 `scripts/generate_cheatsheet.py` 重新生成速查表。

### 命令行参数

```bash
python scripts/generate_cheatsheet.py --lang zh --no-open
```

- `-o, --output`: 自定义输出路径
- `-lang, --lang`: 语言 (`zh` 或 `en`)
- `-d, --skill-dir`: 追加额外的扫描目录，格式 `path:source`
- `--no-open`: 生成后不自动打开浏览器
