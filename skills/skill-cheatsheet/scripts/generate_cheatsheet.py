#!/usr/bin/env python3
"""
Skills Cheatsheet Generator

自动扫描所有已安装的 skills，生成 Anthropic 品牌风格的 HTML 速查表。
"""

import os
import re
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional, Set

import yaml


SCRIPT_PATH = Path(__file__).resolve()
REPO_SKILLS_DIR = SCRIPT_PATH.parents[2]
AGENT_PLATFORM_DIR = SCRIPT_PATH.parents[3]
DEFAULT_UPSTREAM_MANIFEST = AGENT_PLATFORM_DIR / "migration" / "upstream-manifest.yaml"


@dataclass
class SkillInfo:
    name: str
    description: str
    path: str
    is_user: bool = False
    source_kind: str = "custom"
    source_key: str = "custom"
    source_label: str = ""


class SkillsScanner:
    """扫描所有已安装的 skills"""

    # 中文描述映射（完整翻译，非概括）
    DESCRIPTIONS_ZH = {
        'algorithmic-art': '使用 p5.js 创建算法艺术，支持随机种子和交互参数探索。用于用户请求使用代码创建艺术、生成艺术、算法艺术、流场或粒子系统时。创建原创的算法艺术以避免版权问题',
        'brand-guidelines': '应用 Anthropic 官方品牌配色和字体排版。当品牌配色、样式指南、视觉格式或公司设计标准适用时使用',
        'canvas-design': '使用设计理念创建精美的视觉艺术 PNG 和 PDF 文档。当用户要求创建海报、艺术品、设计或其他静态作品时使用。创作原创视觉设计，避免复制现有艺术家作品',
        'doc-coauthoring': '指导用户完成协作编写文档的结构化工作流程。当用户想要编写文档、提案、技术规范、决策文档或类似结构化内容时使用。此工作流程帮助用户高效传递上下文、通过迭代完善内容并验证文档对读者的有效性',
        'docx': '专业的文档创建、编辑和分析，支持修订模式、批注、格式保留和文本提取。当 Claude 需要处理专业文档（.docx 文件）时使用：创建新文档、修改或编辑内容、处理修订模式、添加批注或其他文档任务',
        'frontend-design': '创建具有高设计质量的生产级前端界面。当用户要求构建网页组件、页面、artifacts、海报或应用程序（例如网站、落地页、仪表盘、React 组件、HTML/CSS 布局或美化任何 Web UI）时使用此技能。生成富有创意、精美的代码和 UI 设计，避免通用的 AI 美学风格',
        'internal-comms': '帮助我撰写各类内部沟通的文案资源，使用公司喜欢的格式。当被要求撰写某种内部沟通（状态报告、领导层更新、3P 更新、公司通讯、FAQ、事故报告、项目更新等）时，Claude 应使用此技能',
        'katex-formula-converter': '通用公式转换器，将各种格式的数学表达式规范化为 KaTeX 语法。当用户需要转换公式时使用：Microsoft Word 公式（OMML/MathML）、需要清理的 LaTeX 代码、需要 OCR 的公式图片、格式不一致的 PDF 提取公式、任何混合格式的公式输入。在涉及公式转换、数学表达式规范化或 KaTeX 语法生成的请求时触发',
        'mcp-builder': '创建高质量 MCP（模型上下文协议）服务器的指南，使 LLM 能够通过精心设计的工具与外部服务交互。用于构建 MCP 服务器以集成外部 API 或服务，无论是 Python（FastMCP）还是 Node/TypeScript（MCP SDK）',
        'pdf': '全面的 PDF 操作工具包，用于提取文本和表格、创建新 PDF、合并/拆分文档以及处理表单。当 Claude 需要填写 PDF 表单或以编程方式处理、生成或大规模分析 PDF 文档时使用',
        'pptx': '演示文稿创建、编辑和分析。当 Claude 需要处理演示文稿（.pptx 文件）时使用：创建新演示文稿、修改或编辑内容、处理布局、添加批注或演讲者备注，或其他演示文稿任务',
        'skill-creator': '创建有效技能的指南。当用户想要创建新技能（或更新现有技能）以扩展 Claude 的能力、添加专业化知识、工作流程或工具集成时，应使用此技能',
        'slack-gif-creator': '为 Slack 创建优化动画 GIF 的知识和实用工具。提供约束、验证工具和动画概念。当用户请求为 Slack 制作动画 GIF 时使用，如"为我制作一个 X 做 Y 的 Slack GIF"',
        'theme-factory': '为 artifacts 应用主题的工具包。这些 artifacts 可以是幻灯片、文档、报告、HTML 落地页等。有 10 种预设主题，带有可应用于任何已创建 artifact 的颜色和字体，或可以即时生成新主题',
        'webapp-testing': '使用 Playwright 与本地 Web 应用交互和测试的工具包。支持验证前端功能、调试 UI 行为、捕获浏览器截图和查看浏览器日志',
        'web-artifacts-builder': '用于创建复杂的多组件 claude.ai HTML artifacts 的工具套件，使用现代前端 Web 技术（React、Tailwind CSS、shadcn/ui）。用于需要状态管理、路由或 shadcn/ui 组件的复杂 artifacts - 不适用于简单的单文件 HTML/JSX artifacts',
        'xlsx': '全面的电子表格创建、编辑和分析，支持公式、格式设置、数据分析和可视化。当 Claude 需要处理电子表格（.xlsx、.xlsm、.csv、.tsv 等）时使用：创建带有公式和格式的新电子表格、读取或分析数据、在保留公式的同时修改现有电子表格、电子表格中的数据分析和可视化，或重新计算公式',
    }

    def __init__(
        self,
        root_dir: Optional[Path] = None,
        platform: str = 'codex',
        repo_skills_dir: Optional[Path] = None,
        upstream_manifest_path: Optional[Path] = None,
        lang: str = 'zh',
    ):
        self.platform = platform
        self.root_dir = root_dir or (Path.home() / (".codex" if platform == "codex" else ".claude"))
        self.skills_dir = self.root_dir / "skills"
        self.system_skills_dir = self.skills_dir / ".system"
        self.superpowers_dir = self.root_dir / "superpowers" / "skills"
        self.marketplace_dir = self.root_dir / "plugins" / "marketplaces" / "anthropic-agent-skills" / "skills"
        self.repo_skills_dir = (repo_skills_dir or REPO_SKILLS_DIR).resolve()
        self.upstream_manifest_path = upstream_manifest_path or DEFAULT_UPSTREAM_MANIFEST
        self.upstream_sources = self._load_upstream_sources(self.upstream_manifest_path)
        self.lang = lang

    def scan_all(self) -> List[SkillInfo]:
        """扫描所有 skills"""
        all_skills = []

        if self.platform == 'codex':
            all_skills.extend(self._scan_user_skills())
            all_skills.extend(self._scan_system_skills())
            all_skills.extend(self._scan_superpowers_skills())
        else:
            all_skills.extend(self._scan_user_skills())
            all_skills.extend(self._scan_marketplace_skills())

        return all_skills

    def _load_upstream_sources(self, manifest_path: Path) -> Dict[str, Dict[str, str]]:
        if not manifest_path.exists():
            return {}

        data = yaml.safe_load(manifest_path.read_text(encoding='utf-8')) or {}
        upstream_map: Dict[str, Dict[str, str]] = {}
        for upstream in data.get('upstreams', []):
            upstream_id = upstream.get('id', 'upstream')
            upstream_label = upstream.get('label', upstream_id)
            for skill in upstream.get('tracked_skills', []):
                name = skill.get('name')
                if not name:
                    continue
                upstream_map[name] = {
                    'id': upstream_id,
                    'label': upstream_label,
                }
        return upstream_map

    def _scan_user_skills(self) -> List[SkillInfo]:
        """扫描用户自定义 skills"""
        skills = []
        if not self.skills_dir.exists():
            return skills

        for item in self.skills_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                skill_md = item / "SKILL.md"
                if skill_md.exists():
                    source_kind, source_key, source_label = self._classify_repo_skill(item)
                    info = self._parse_skill_md(
                        skill_md,
                        is_user=source_kind in {'local', 'custom'},
                        source_kind=source_kind,
                        source_key=source_key,
                        source_label=source_label,
                    )
                    if info:
                        skills.append(info)

        return skills

    def _scan_system_skills(self) -> List[SkillInfo]:
        """扫描 Codex 内建 .system skills"""
        skills = []
        if not self.system_skills_dir.exists():
            return skills

        for item in self.system_skills_dir.iterdir():
            if item.is_dir():
                skill_md = item / "SKILL.md"
                if skill_md.exists():
                    info = self._parse_skill_md(
                        skill_md,
                        is_user=False,
                        source_kind='system',
                        source_key='system',
                        source_label='System Built-in',
                    )
                    if info:
                        skills.append(info)

        return skills

    def _scan_superpowers_skills(self) -> List[SkillInfo]:
        """扫描 Codex superpowers skills"""
        skills = []
        if not self.superpowers_dir.exists():
            return skills

        for item in self.superpowers_dir.iterdir():
            if item.is_dir():
                skill_md = item / "SKILL.md"
                if skill_md.exists():
                    info = self._parse_skill_md(
                        skill_md,
                        is_user=False,
                        source_kind='superpower',
                        source_key='third-party',
                        source_label='Third-Party Repo',
                    )
                    if info:
                        skills.append(info)

        return skills

    def _scan_marketplace_skills(self) -> List[SkillInfo]:
        """扫描 marketplace skills"""
        skills = []
        if not self.marketplace_dir.exists():
            return skills

        for item in self.marketplace_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                skill_md = item / "SKILL.md"
                if skill_md.exists():
                    info = self._parse_skill_md(
                        skill_md,
                        is_user=False,
                        source_kind='marketplace',
                        source_key='marketplace',
                        source_label='Marketplace',
                    )
                    if info:
                        skills.append(info)

        return skills

    def _classify_repo_skill(self, skill_dir: Path) -> tuple[str, str, str]:
        try:
            resolved = skill_dir.resolve()
        except OSError:
            resolved = skill_dir

        if resolved.is_relative_to(self.repo_skills_dir):
            upstream = self.upstream_sources.get(skill_dir.name)
            if upstream:
                source_label = upstream['label']
                source_key = 'anthropic-official' if source_label == 'Anthropic Official' else 'third-party'
                return 'upstream', source_key, source_label
            return 'local', 'local', 'Local Maintained'
        return 'custom', 'custom', '自定义'

    def _parse_skill_md(
        self,
        md_path: Path,
        is_user: bool,
        source_kind: str,
        source_key: str,
        source_label: str,
    ) -> Optional[SkillInfo]:
        """解析 SKILL.md 文件"""
        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 提取 YAML frontmatter
            frontmatter = self._extract_frontmatter(content)
            if not frontmatter:
                return None

            name = frontmatter.get('name', md_path.parent.name)
            description = frontmatter.get('description', '')

            # 清理描述中的引号
            description = description.strip('"').strip("'")

            # 应用中文翻译
            if self.lang == 'zh' and name in self.DESCRIPTIONS_ZH:
                description = self.DESCRIPTIONS_ZH[name]

            return SkillInfo(
                name=name,
                description=description,
                path=str(md_path.parent),
                is_user=is_user,
                source_kind=source_kind,
                source_key=source_key,
                source_label=source_label,
            )
        except Exception as e:
            print(f"Warning: Failed to parse {md_path}: {e}")
            return None

    def _extract_frontmatter(self, content: str) -> Optional[Dict]:
        """提取 YAML frontmatter"""
        match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not match:
            return None
        return yaml.safe_load(match.group(1)) or {}


class SkillsClassifier:
    """对 skills 进行分类"""

    # 文档处理类
    DOC_KEYWORDS = ['pdf', 'docx', 'ppt', 'pptx', 'xlsx', 'xls', 'document', 'formula', 'katex', 'word', 'excel', 'powerpoint']

    # 设计创意类
    DESIGN_KEYWORDS = ['art', 'design', 'canvas', 'frontend', 'web', 'theme', 'gif', 'slack', 'brand', 'algorithmic', 'visual']

    # 开发工具类
    CODE_KEYWORDS = ['mcp', 'testing', 'test', 'skill-creator', 'developer', 'build', 'code']

    # 沟通协作类
    COMM_KEYWORDS = ['communication', 'comms', 'internal', 'doc-coauthoring', 'proposal', 'report']

    def classify(self, skill: SkillInfo) -> str:
        """分类 skill"""
        name_lower = skill.name.lower()
        desc_lower = skill.description.lower()

        text = f"{name_lower} {desc_lower}"

        # 检查各类关键词
        if any(kw in text for kw in self.DOC_KEYWORDS):
            return 'doc'
        elif any(kw in text for kw in self.DESIGN_KEYWORDS):
            return 'design'
        elif any(kw in text for kw in self.CODE_KEYWORDS):
            return 'code'
        elif any(kw in text for kw in self.COMM_KEYWORDS):
            return 'comm'
        else:
            return 'design'  # 默认


class CheatsheetGenerator:
    """生成 HTML 速查表"""

    # 分类信息
    CATEGORIES = {
        'doc': {
            'name': '文档与文件处理',
            'color': '#d97757',
            'gradient': 'linear-gradient(135deg, #d97757, #c96b4d)'
        },
        'design': {
            'name': '设计与创意',
            'color': '#6a9bcc',
            'gradient': 'linear-gradient(135deg, #6a9bcc, #5a8fb8)'
        },
        'code': {
            'name': '开发与工具',
            'color': '#788c5d',
            'gradient': 'linear-gradient(135deg, #788c5d, #6a7c52)'
        },
        'comm': {
            'name': '沟通与文档',
            'color': '#b0aea5',
            'gradient': 'linear-gradient(135deg, #b0aea5, #a2a097)'
        }
    }

    # 图标映射
    ICONS = {
        'doc': {'pdf': 'PDF', 'docx': 'DOC', 'pptx': 'PPT', 'xlsx': 'XLS', 'katex': '公式'},
        'design': {'algorithmic-art': '生成', 'canvas-design': '画布', 'frontend-design': '前端',
                   'web-artifacts-builder': 'Web', 'theme-factory': '主题', 'slack-gif-creator': '动图',
                   'brand-guidelines': '品牌'},
        'code': {'mcp-builder': 'MCP', 'webapp-testing': '测试', 'skill-creator': '技能'},
        'comm': {'doc-coauthoring': '文档', 'internal-comms': '沟通'}
    }

    # 触发词映射
    TRIGGER_HINTS = {
        'pdf': '处理PDF、填写表单、提取PDF内容',
        'docx': '创建Word文档、修订模式、批注',
        'pptx': '制作PPT、创建幻灯片、演示文稿',
        'xlsx': 'Excel表格、电子表格、公式计算',
        'katex-formula-converter': '公式转换、数学公式、KaTeX、Word公式',
        'algorithmic-art': '生成艺术、算法艺术、p5.js、流场图',
        'canvas-design': '设计海报、创作艺术、视觉设计',
        'frontend-design': '创建网页、前端界面、React组件',
        'web-artifacts-builder': '交互式工具、复杂Web应用、状态管理',
        'theme-factory': '应用主题、配色方案、样式美化',
        'slack-gif-creator': '制作GIF、动画、Slack动图',
        'brand-guidelines': '品牌配色、Anthropic风格、官方样式',
        'mcp-builder': '创建MCP服务器、API集成、外部服务',
        'webapp-testing': '测试网页、Playwright、浏览器测试',
        'skill-creator': '创建skill、自定义技能、扩展功能',
        'doc-coauthoring': '编写文档、技术规范、项目提案',
        'internal-comms': '状态报告、内部通知、工作汇报',
        'skill-cheatsheet': '生成技能速查表、更新cheatsheet、查看已安装技能'
    }

    SOURCE_META = {
        'upstream': {
            'zh': 'Anthropic Official',
            'en': 'UPSTREAM',
            'class': 'badge-upstream',
            'color': '#2f6f57',
        },
        'local': {
            'zh': 'Local Maintained',
            'en': 'LOCAL',
            'class': 'badge-local',
            'color': '#141413',
        },
        'system': {
            'zh': 'System Built-in',
            'en': 'SYSTEM',
            'class': 'badge-system',
            'color': '#6c63a6',
        },
        'superpower': {
            'zh': 'Third-Party Repo',
            'en': 'SUPERPOWER',
            'class': 'badge-superpower',
            'color': '#9b6c32',
        },
        'marketplace': {
            'zh': 'Marketplace',
            'en': 'MARKETPLACE',
            'class': 'badge-marketplace',
            'color': '#2f5d8a',
        },
        'custom': {
            'zh': '自定义',
            'en': 'CUSTOM',
            'class': 'badge-custom',
            'color': '#141413',
        },
    }

    TYPE_META = {
        'doc': {'zh': '文档', 'en': 'Documents', 'class': 'badge-type-doc'},
        'design': {'zh': '设计', 'en': 'Design', 'class': 'badge-type-design'},
        'code': {'zh': '开发', 'en': 'Development', 'class': 'badge-type-code'},
        'comm': {'zh': '沟通', 'en': 'Communication', 'class': 'badge-type-comm'},
    }

    def __init__(self, lang: str = 'zh', platform: str = 'codex'):
        self.lang = lang
        self.platform = platform
        self.classifier = SkillsClassifier()

    def get_icon(self, skill: SkillInfo, category: str) -> str:
        """获取技能图标文字"""
        if skill.is_user:
            if skill.name == 'katex-formula-converter':
                return '公式'
            return '自'
        return self.ICONS.get(category, {}).get(skill.name, skill.name[:4].upper())

    def get_trigger_hint(self, skill: SkillInfo) -> str:
        """获取触发词提示"""
        hint = self.TRIGGER_HINTS.get(skill.name, '')
        if self.lang == 'zh':
            return f"触发词：{hint}" if hint else ""
        return f"Trigger: {hint}" if hint else ""

    def generate(self, skills: List[SkillInfo], output_path: Path) -> str:
        """生成 HTML"""
        # 分类 skills
        categorized = {cat: [] for cat in self.CATEGORIES}
        for skill in skills:
            cat = self.classifier.classify(skill)
            categorized[cat].append(skill)

        # 生成 HTML
        html = self._render_html(categorized, len(skills))

        # 写入文件
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        return str(output_path)

    def _render_html(self, categorized: Dict[str, List[SkillInfo]], total_count: int) -> str:
        """渲染 HTML"""
        is_zh = self.lang == 'zh'
        platform_title = 'Codex' if self.platform == 'codex' else 'Claude Code'

        html = f"""<!DOCTYPE html>
<html lang="{'zh-CN' if is_zh else 'en'}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{platform_title} Skills {'速查表' if is_zh else 'Cheatsheet'}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family={'Noto+Sans+CT:wght@400;500;600;700&Noto+Serif+SC:wght@400;500;600' if is_zh else 'Poppins:wght@400;500;600;700&family=Lora:wght@400;500;600'}&display=swap');

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: {'Noto Serif SC, Songti SC, serif' if is_zh else 'Lora, Georgia, serif'};
            background: #faf9f5;
            color: #141413;
            line-height: 1.6;
            padding: 40px;
        }}

        .container {{ max-width: 1400px; margin: 0 auto; }}

        header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid #d97757;
        }}

        h1 {{
            font-family: {'Noto Sans SC, PingFang SC' if is_zh else 'Poppins, Arial'}, sans-serif;
            font-size: 42px;
            font-weight: 600;
            color: #141413;
            margin-bottom: 8px;
        }}

        .subtitle {{
            font-family: {'Noto Sans SC, PingFang SC' if is_zh else 'Poppins, Arial'}, sans-serif;
            font-size: 14px;
            color: #b0aea5;
            letter-spacing: {3 if is_zh else 2}px;
            { 'text-transform: uppercase;' if not is_zh else '' }
        }}

        .section {{ margin-bottom: 30px; }}

        .section-title {{
            font-family: {'Noto Sans SC, PingFang SC' if is_zh else 'Poppins, Arial'}, sans-serif;
            font-size: 18px;
            font-weight: 600;
            color: #6a9bcc;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .section-title::before {{
            content: '';
            width: 8px;
            height: 8px;
            background: #6a9bcc;
            border-radius: 50%;
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
            gap: 16px;
        }}

        .skill-card {{
            background: white;
            border: 1px solid #e8e6dc;
            border-radius: 10px;
            padding: 18px;
            transition: all 0.2s ease;
        }}

        .skill-card.is-hidden {{
            display: none;
        }}

        .skill-card:hover {{
            border-color: #d97757;
            box-shadow: 0 4px 16px rgba(217, 119, 87, 0.15);
            transform: translateY(-2px);
        }}

        .skill-header {{
            display: flex;
            align-items: flex-start;
            gap: 12px;
            margin-bottom: 12px;
        }}

        .skill-icon {{
            width: 40px;
            height: 40px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            font-family: {'Noto Sans SC' if is_zh else 'Poppins'}, sans-serif;
            font-weight: 600;
            font-size: 11px;
            color: white;
            text-align: center;
            line-height: 1.2;
        }}

        .skill-icon.doc {{ background: linear-gradient(135deg, #d97757, #c96b4d); }}
        .skill-icon.design {{ background: linear-gradient(135deg, #6a9bcc, #5a8fb8); }}
        .skill-icon.code {{ background: linear-gradient(135deg, #788c5d, #6a7c52); }}
        .skill-icon.comm {{ background: linear-gradient(135deg, #b0aea5, #a2a097); }}
        .skill-icon.user {{ background: linear-gradient(135deg, #141413, #2a2a29); }}

        .skill-name {{
            font-family: {'Noto Sans SC, PingFang SC' if is_zh else 'Poppins, Arial'}, sans-serif;
            font-size: 16px;
            font-weight: 600;
            color: #141413;
        }}

        .skill-desc {{
            font-size: 14px;
            color: #5c5a54;
            line-height: 1.6;
        }}

        .skill-keywords {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 12px;
        }}

        .keyword {{
            font-family: {'Noto Sans SC' if is_zh else 'Poppins'}, sans-serif;
            font-size: 11px;
            padding: 4px 10px;
            border-radius: 12px;
            background: #f5f4f1;
            color: #5c5a54;
        }}

        .badge {{
            display: inline-block;
            font-family: {'Noto Sans SC' if is_zh else 'Poppins'}, sans-serif;
            font-size: 10px;
            padding: 3px 8px;
            border-radius: 4px;
            margin-left: 8px;
            border: 1px solid transparent;
            appearance: none;
            -webkit-appearance: none;
            background-clip: padding-box;
        }}

        .badge-user {{
            background: #141413;
            color: #faf9f5;
        }}

        .badge-upstream {{
            background: #eef7f2;
            color: #2f6f57;
        }}

        .badge-local {{
            background: #f2f1ec;
            color: #141413;
        }}

        .badge-system {{
            background: #f1effb;
            color: #6c63a6;
        }}

        .badge-superpower {{
            background: #fbf3e8;
            color: #9b6c32;
        }}

        .badge-marketplace {{
            background: #eef4fb;
            color: #2f5d8a;
        }}

        .badge-custom {{
            background: #f5f4f1;
            color: #141413;
        }}

        .summary-groups {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 16px;
            margin-top: 18px;
            margin-bottom: 28px;
        }}

        .summary-block {{
            background: white;
            border: 1px solid #e8e6dc;
            border-radius: 12px;
            padding: 14px 16px;
        }}

        .summary-title {{
            font-family: {'Noto Sans SC' if is_zh else 'Poppins'}, sans-serif;
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 1px;
            color: #b0aea5;
            margin-bottom: 10px;
        }}

        .summary-row {{
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }}

        .summary-pill {{
            font-family: {'Noto Sans SC' if is_zh else 'Poppins'}, sans-serif;
            font-size: 12px;
            padding: 6px 12px;
            border-radius: 999px;
            background: #faf9f5;
            border: 1px solid #ece9de;
            color: #5c5a54;
        }}

        button.summary-pill,
        button.badge {{
            cursor: pointer;
        }}

        button.summary-pill:hover,
        button.badge:hover,
        button.summary-pill.is-active,
        button.badge.is-active {{
            border-color: #d97757;
            color: #141413;
        }}

        .badge-type {{
            background: #f5f4f1;
            color: #5c5a54;
            border: 1px solid #e8e6dc;
        }}

        .toolbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            margin-bottom: 18px;
            flex-wrap: wrap;
        }}

        .filter-status {{
            font-family: {'Noto Sans SC' if is_zh else 'Poppins'}, sans-serif;
            font-size: 13px;
            color: #5c5a54;
        }}

        .clear-filter {{
            font-family: {'Noto Sans SC' if is_zh else 'Poppins'}, sans-serif;
            font-size: 12px;
            padding: 8px 12px;
            border-radius: 999px;
            border: 1px solid #e8e6dc;
            background: white;
            color: #5c5a54;
            cursor: pointer;
        }}

        footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e8e6dc;
            text-align: center;
        }}

        .legend {{
            display: flex;
            gap: 24px;
            justify-content: center;
            margin-bottom: 12px;
            flex-wrap: wrap;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            color: #5c5a54;
        }}

        .legend-dot {{
            width: 12px;
            height: 12px;
            border-radius: 4px;
        }}

        .footer-text {{
            font-size: 13px;
            color: #b0aea5;
        }}

        .trigger-hint {{
            font-family: {'Noto Sans SC' if is_zh else 'Poppins'}, sans-serif;
            font-size: 12px;
            color: #788c5d;
            margin-top: 8px;
            padding: 8px 12px;
            background: #f5f8f2;
            border-radius: 6px;
        }}

        @media print {{
            body {{ padding: 20px; }}
            .skill-card {{ break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="subtitle">{platform_title}</div>
            <h1>Skills {'速查表' if is_zh else 'Cheatsheet'}</h1>
            <p style="color: #b0aea5; font-size: 15px;">{'所有已安装技能的快速参考指南' if is_zh else 'Quick reference guide for all installed skills'}</p>
        </header>
"""
        source_counts = self._count_sources(categorized)
        type_counts = self._count_types(categorized)
        html += f"""
            <div class="summary-groups">
                <div class="summary-block">
                    <div class="summary-title">{'按来源' if is_zh else 'By Source'}</div>
                    <div class="summary-row">
"""
        for source_key, source_info in source_counts.items():
            count = source_info['count']
            if count == 0:
                continue
            label = source_info['label']
            html += (
                f'                        <button type="button" class="summary-pill" '
                f'data-filter-kind="source" data-filter-value="{source_key}" data-filter-label="{label}">{label} · {count}</button>\n'
            )
        html += f"""
                    </div>
                </div>
                <div class="summary-block">
                    <div class="summary-title">{'按类型' if is_zh else 'By Type'}</div>
                    <div class="summary-row">
"""
        for category_key, count in type_counts.items():
            if count == 0:
                continue
            meta = self.TYPE_META[category_key]
            label = meta['zh'] if is_zh else meta['en']
            html += (
                f'                        <button type="button" class="summary-pill" '
                f'data-filter-kind="type" data-filter-value="{category_key}">{label} · {count}</button>\n'
            )
        html += """
                    </div>
                </div>
            </div>
"""
        html += f"""
        <div class="toolbar">
            <div class="filter-status" id="filter-status">{'当前显示全部技能' if is_zh else 'Showing all skills'}</div>
            <button type="button" class="clear-filter" id="clear-filters">{'清除筛选' if is_zh else 'Clear filters'}</button>
        </div>
"""

        # 渲染各类别的 skills
        for cat, cat_info in self.CATEGORIES.items():
            skills = categorized.get(cat, [])
            if not skills:
                continue

            html += f"""
        <div class="section">
            <div class="section-title">{cat_info['name']}</div>
            <div class="grid">
"""
            for skill in skills:
                html += self._render_skill_card(skill, cat)
            html += """
            </div>
        </div>
"""

        # 渲染页脚
        legend_items = [
            ('#d97757', '文档处理' if is_zh else 'Documents'),
            ('#6a9bcc', '设计创意' if is_zh else 'Design'),
            ('#788c5d', '开发工具' if is_zh else 'Development'),
            ('#b0aea5', '沟通协作' if is_zh else 'Communication'),
            ('#2f6f57', 'Anthropic Official' if is_zh else 'Upstream'),
            ('#141413', 'Local Maintained' if is_zh else 'Local'),
            ('#6c63a6', 'System Built-in' if is_zh else 'System'),
            ('#9b6c32', 'Third-Party Repo' if is_zh else 'Third-Party'),
        ]

        html += """
        <footer>
            <div class="legend">
"""
        for color, label in legend_items:
            html += f'<div class="legend-item"><div class="legend-dot" style="background: {color};"></div> {label}</div>\n'

        html += f"""
            </div>
            <p class="footer-text">{platform_title} {'技能速查表' if is_zh else 'Skills Cheatsheet'} • {total_count} {'个技能已安装' if is_zh else 'skills installed'}</p>
        </footer>
    </div>
    <script>
        const activeFilters = {{ source: null, type: null }};

        function updateFilterStatus() {{
            const status = document.getElementById('filter-status');
            const labels = [];
            const sourceButton = document.querySelector(`[data-filter-kind="source"][data-filter-value="${{activeFilters.source}}"]`);
            const typeButton = document.querySelector(`[data-filter-kind="type"][data-filter-value="${{activeFilters.type}}"]`);
            if (activeFilters.source && sourceButton) labels.push(`{'来源' if is_zh else 'Source'}: ${{sourceButton.dataset.filterLabel || activeFilters.source}}`);
            if (activeFilters.type && typeButton) labels.push(`{'类型' if is_zh else 'Type'}: ${{typeButton.dataset.filterLabel || activeFilters.type}}`);
            status.textContent = labels.length ? labels.join(' · ') : "{'当前显示全部技能' if is_zh else 'Showing all skills'}";
        }}

        function updateActiveButtons() {{
            document.querySelectorAll('[data-filter-kind]').forEach((button) => {{
                const kind = button.dataset.filterKind;
                const value = button.dataset.filterValue;
                button.classList.toggle('is-active', activeFilters[kind] === value);
            }});
        }}

        function applyFilters() {{
            document.querySelectorAll('.skill-card').forEach((card) => {{
                const sourceMatch = !activeFilters.source || card.dataset.source === activeFilters.source;
                const typeMatch = !activeFilters.type || card.dataset.type === activeFilters.type;
                card.classList.toggle('is-hidden', !(sourceMatch && typeMatch));
            }});
            updateFilterStatus();
            updateActiveButtons();
        }}

        document.querySelectorAll('[data-filter-kind]').forEach((button) => {{
            button.addEventListener('click', () => {{
                const kind = button.dataset.filterKind;
                const value = button.dataset.filterValue;
                activeFilters[kind] = activeFilters[kind] === value ? null : value;
                applyFilters();
            }});
        }});

        document.getElementById('clear-filters').addEventListener('click', () => {{
            activeFilters.source = null;
            activeFilters.type = null;
            applyFilters();
        }});

        applyFilters();
    </script>
</body>
</html>
"""
        return html

    def _render_skill_card(self, skill: SkillInfo, category: str) -> str:
        """渲染单个 skill 卡片"""
        is_zh = self.lang == 'zh'
        icon = self.get_icon(skill, category)
        icon_class = 'user' if skill.is_user else category
        source_badge = self._render_source_badge(skill, is_zh)
        type_badge = self._render_type_badge(category, is_zh)
        trigger_hint = self.get_trigger_hint(skill)

        # 提取关键词
        keywords = self._extract_keywords(skill.description, is_zh)

        return f"""
                <div class="skill-card" data-source="{skill.source_key}" data-type="{category}">
                    <div class="skill-header">
                        <div class="skill-icon {icon_class}">{icon}</div>
                        <div class="skill-name">{skill.name}{source_badge}{type_badge}</div>
                    </div>
                    <div class="skill-desc">{skill.description}</div>
                    <div class="skill-keywords">
                        {keywords}
                    </div>
                    {f'<div class="trigger-hint">{trigger_hint}</div>' if trigger_hint else ''}
                </div>"""

    def _render_source_badge(self, skill: SkillInfo, is_zh: bool) -> str:
        meta = self.SOURCE_META.get(skill.source_kind, self.SOURCE_META['custom'])
        label = skill.source_label or (meta['zh'] if is_zh else meta['en'])
        return (
            f' <button type="button" class="badge {meta["class"]}" '
            f'data-filter-kind="source" data-filter-value="{skill.source_key}" data-filter-label="{label}">{label}</button>'
        )

    def _render_type_badge(self, category: str, is_zh: bool) -> str:
        meta = self.TYPE_META[category]
        label = meta['zh'] if is_zh else meta['en']
        return (
            f' <button type="button" class="badge badge-type" '
            f'data-filter-kind="type" data-filter-value="{category}">{label}</button>'
        )

    def _count_sources(self, categorized: Dict[str, List[SkillInfo]]) -> Dict[str, Dict[str, str | int]]:
        counts: Dict[str, Dict[str, str | int]] = {}
        for skills in categorized.values():
            for skill in skills:
                if skill.source_key not in counts:
                    counts[skill.source_key] = {
                        'label': self._display_source_label(skill),
                        'count': 0,
                    }
                counts[skill.source_key]['count'] += 1
        return counts

    def _display_source_label(self, skill: SkillInfo) -> str:
        return skill.source_label or self.SOURCE_META.get(skill.source_kind, self.SOURCE_META['custom'])['zh']

    def _count_types(self, categorized: Dict[str, List[SkillInfo]]) -> Dict[str, int]:
        return {category: len(skills) for category, skills in categorized.items()}

    def _extract_keywords(self, description: str, is_zh: bool) -> str:
        """从描述中提取关键词"""
        # 简单提取前3个关键词（实际可以用更复杂的逻辑）
        keywords = []

        # 查找常见关键词
        common_patterns = [
            r'(PDF|Word|Excel|PowerPoint|PPT|DOCX|XLSX)',
            r'(React|Vue|HTML|CSS|Tailwind)',
            r'(API|MCP|REST)',
            r'(p5\.js|Playwright)',
            r'(文档|表格|幻灯片|公式|图表)',
        ]

        for pattern in common_patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            keywords.extend(matches[:2])

        # 取前4个
        keywords = keywords[:4]

        return ''.join(f'<span class="keyword">{kw}</span>' for kw in keywords)


def generate(
    output: Optional[str] = None,
    lang: str = 'zh',
    claude_dir: Optional[str] = None,
    open_browser: bool = True,
    platform: str = 'codex',
    repo_skills_dir: Optional[str] = None,
    upstream_manifest_path: Optional[str] = None,
) -> str:
    """
    生成 Skills 速查表

    Args:
        output: 输出文件路径，默认 ~/.codex/skills/skills-cheatsheet.html 或 ~/.claude/skills/skills-cheatsheet.html
        lang: 语言，'zh' 或 'en'
        claude_dir: 平台根目录，默认依据 platform 选择 ~/.codex 或 ~/.claude
        open_browser: 是否自动打开浏览器

    Returns:
        生成的文件路径
    """
    root_dir = Path(claude_dir) if claude_dir else Path.home() / (".codex" if platform == "codex" else ".claude")
    output_path = Path(output) if output else root_dir / "skills" / "skills-cheatsheet.html"

    # 扫描 skills
    scanner = SkillsScanner(
        root_dir=root_dir,
        platform=platform,
        repo_skills_dir=Path(repo_skills_dir) if repo_skills_dir else None,
        upstream_manifest_path=Path(upstream_manifest_path) if upstream_manifest_path else None,
        lang=lang,
    )
    skills = scanner.scan_all()

    # 按名称排序
    skills.sort(key=lambda s: s.name.lower())

    # 生成 HTML
    generator = CheatsheetGenerator(lang=lang, platform=platform)
    result_path = generator.generate(skills, output_path)

    print(f"✅ Generated: {result_path}")
    print(f"   Found {len(skills)} skills")

    # 打开浏览器
    if open_browser:
        import subprocess
        try:
            subprocess.run(['xdg-open', result_path], check=False)
        except Exception:
            pass

    return result_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate skills cheatsheet")
    parser.add_argument('-o', '--output', help='Output file path')
    parser.add_argument('-lang', '--lang', default='zh', choices=['zh', 'en'], help='Language')
    parser.add_argument('-c', '--claude-dir', help='Platform root directory path')
    parser.add_argument('--platform', default='codex', choices=['codex', 'claude'], help='Target platform')
    parser.add_argument('--repo-skills-dir', help='Repo-managed skills directory path')
    parser.add_argument('--upstream-manifest', help='Upstream manifest path')
    parser.add_argument('--no-open', action='store_true', help='Do not open browser')

    args = parser.parse_args()

    generate(
        output=args.output,
        lang=args.lang,
        claude_dir=args.claude_dir,
        open_browser=not args.no_open,
        platform=args.platform,
        repo_skills_dir=args.repo_skills_dir,
        upstream_manifest_path=args.upstream_manifest,
    )
