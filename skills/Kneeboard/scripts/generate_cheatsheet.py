#!/usr/bin/env python3
"""
Skills Cheatsheet Generator

自动扫描所有已安装的 coding-agent skills，生成 Anthropic 品牌风格的 HTML 速查表。
支持多个运行时目录：~/.agents/skills、~/.claude/skills、~/.codex/skills、~/.pi/skills 等。
自动识别上游仓库来源（gstack、anthropics、superpowers、agent-skills 等）。
"""

import os
import re
import yaml
import argparse
import webbrowser
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional, Set, Tuple


DEFAULT_OUTPUT_PATH = Path("/media/yhr/2T/Canon/artifacts/generated/skills-cheatsheet.html")


@dataclass
class SkillInfo:
    name: str
    description: str
    path: str
    source: str = "agent"      # runtime: agent, claude, codex, pi, marketplace
    upstream: str = "local"    # upstream: gstack, anthropics, superpowers, agent-skills, planning-with-files, local


class SkillsScanner:
    """扫描所有已安装的 skills"""

    # 中文描述映射（完整翻译，非概括）
    DESCRIPTIONS_ZH = {
        # 文档处理
        'pdf': '全面的 PDF 操作工具包，用于提取文本和表格、创建新 PDF、合并/拆分文档以及处理表单。当需要填写 PDF 表单或以编程方式处理、生成或大规模分析 PDF 文档时使用',
        'docx': '专业的 Word 文档创建、编辑和分析，支持修订模式、批注、格式保留和文本提取。当需要处理 .docx 文件时使用：创建新文档、修改或编辑内容、处理修订模式、添加批注或其他文档任务',
        'pptx': '演示文稿创建、编辑和分析。当需要处理 .pptx 文件时使用：创建新演示文稿、修改或编辑内容、处理布局、添加批注或演讲者备注，或其他演示文稿任务',
        'xlsx': '全面的电子表格创建、编辑和分析，支持公式、格式设置、数据分析和可视化。当需要处理 .xlsx、.csv、.tsv 等文件时使用：创建带有公式和格式的新电子表格、读取或分析数据、修改现有电子表格、数据分析与可视化',
        'katex-formula-converter': '通用公式转换器，将各种格式的数学表达式规范化为 KaTeX 语法。支持 Microsoft Word 公式（OMML/MathML）、需要清理的 LaTeX 代码、需要 OCR 的公式图片、格式不一致的 PDF 提取公式',
        # 设计创意
        'algorithmic-art': '使用 p5.js 创建算法艺术，支持随机种子和交互参数探索。用于请求使用代码创建艺术、生成艺术、算法艺术、流场或粒子系统时。创作原创算法艺术以避免版权问题',
        'brand-guidelines': '应用 Anthropic 官方品牌配色和字体排版。当品牌配色、样式指南、视觉格式或公司设计标准适用时使用',
        'canvas-design': '使用设计理念创建精美的视觉艺术 PNG 和 PDF 文档。当用户要求创建海报、艺术品、设计或其他静态作品时使用。创作原创视觉设计，避免复制现有艺术家作品',
        'frontend-design': '创建具有高设计质量的生产级前端界面。当用户要求构建网页组件、页面、海报或应用程序（例如网站、落地页、仪表盘、React 组件、HTML/CSS 布局或美化任何 Web UI）时使用。生成富有创意、精美的代码和 UI 设计，避免通用的 AI 美学风格',
        'theme-factory': '为 artifacts 应用主题的工具包。这些 artifacts 可以是幻灯片、文档、报告、HTML 落地页等。有 10 种预设主题，带有可应用于任何已创建 artifact 的颜色和字体，或可以即时生成新主题',
        # 开发工具
        'mcp-builder': '创建高质量 MCP（模型上下文协议）服务器的指南，使 LLM 能够通过精心设计的工具与外部服务交互。用于构建 MCP 服务器以集成外部 API 或服务，无论是 Python（FastMCP）还是 Node/TypeScript（MCP SDK）',
        'skill-creator': '创建有效技能的指南。当用户想要创建新技能（或更新现有技能）以扩展能力、添加专业化知识、工作流程或工具集成时应使用此技能',
        'skill-cheatsheet': '生成 Skills 速查表。自动扫描所有已安装的 skills，生成 Anthropic 品牌风格的 HTML 速查表。包含每个 skill 的名称、描述、触发词和分类',
        # agents skills 中文描述
        'adapt': '适配设计以在不同屏幕尺寸、设备、上下文或平台上工作。实现断点、流体布局和触控目标。用于响应式设计、移动布局、断点、视口适配或跨设备兼容性',
        'animate': '为功能添加有目的的动画、微交互和运动效果，以提升可用性和愉悦感。用于添加动画、过渡、微交互、运动设计、悬停效果或让 UI 更有活力',
        'arrange': '改善布局、间距和视觉节奏。修复单调的网格、不一致的间距和薄弱的视觉层次。用于布局感觉不对、间距问题、视觉层次、拥挤的 UI、对齐问题或想要更好的构图',
        'audit': '运行技术质量检查，涵盖无障碍、性能、主题、响应式设计和反模式。生成带有 P0-P3 严重等级和可操作计划的评分报告。用于无障碍检查、性能审计或技术质量审查',
        'autoplan': '自动审查流水线——读取完整的 CEO、设计、工程和 DX 审查技能并按顺序运行自动决策。在最后审批 gate 呈现品味决策。用于"自动审查"、"autoplan"、"运行所有审查"',
        'benchmark': '使用浏览守护进程进行性能回归检测。建立页面加载时间、Core Web Vitals 和资源大小的基线。比较每次 PR 的前后差异。用于性能、基准测试、页面速度、lighthouse、web vitals、包大小、加载时间',
        'bolder': '放大安全或乏味的设计，使其在视觉上有趣和刺激。在保持可用性的同时增加影响力。用于设计看起来平淡、普通、太安全、缺乏个性或想要更多视觉冲击力',
        'brainstorming': '在任何创意工作之前使用——创建功能、构建组件、添加功能或修改行为。探索用户意图、需求和设计',
        'browse': '用于 QA 测试和站点 dogfooding 的快速 headless 浏览器。导航任何 URL、与元素交互、验证页面状态、差异前后操作、捕获带注释的屏幕截图、检查响应式布局、测试表单和上传、处理对话框、断言元素状态',
        'canary': '部署后金丝雀监控。监视线上应用的控制台错误、性能回归和页面故障。定期捕获屏幕截图、与部署前基线比较并在异常时发出警报。用于"监控部署"、"金丝雀"、"部署后检查"',
        'capture-mistake-rule': '当错误、误读需求、重复实现错误或重要教训应被记录为持久规则以免重复时使用。触发词："把它写成规则"、"记住这个错误"、"吸取经验教训"、"添加护栏"',
        'careful': '破坏性命令的安全护栏。在 rm -rf、DROP TABLE、force-push、git reset --hard、kubectl delete 等之前发出警告。用于触碰生产环境、调试实时系统或共享环境',
        'clarify': '改善不清晰的 UX 文案、错误消息、微文案、标签和说明，使界面更易于理解。用于令人困惑的文本、不清晰的标签、糟糕的错误消息、难以遵循的说明或想要更好的 UX 写作',
        'code-reviewer': '当用户要求进行代码审查、最近更改审查、差异审查、PR 风格审查、bug 风险检查或回归扫描时使用。关注正确性、回归、安全性和可维护性',
        'codex': 'OpenAI Codex CLI 包装器——三种模式。代码审查：通过 codex review 进行独立差异审查。挑战：试图破坏你的代码的对抗模式。咨询：向 codex 提问。用于"codex review"、"codex challenge"、"ask codex"、"second opinion"',
        'colorize': '为过于单色或缺乏视觉趣味的功能添加战略性颜色，使界面更引人入胜和富有表现力。用于设计看起来灰暗、沉闷、缺乏温暖、需要更多颜色或想要更生动的调色板',
        'critique': '从 UX 角度评估设计，评估视觉层次、信息架构、情感共鸣、认知负荷和整体质量。带有定量评分、基于角色的测试、自动反模式检测和可操作反馈',
        'cso': '首席安全官模式。基础设施优先的安全审计：秘密考古、依赖供应链、CI/CD 管道安全、LLM/AI 安全、技能供应链扫描，以及 OWASP Top 10、STRIDE 威胁建模和主动验证。用于"安全审计"、"威胁模型"、"渗透测试审查"',
        'delight': '添加快乐、个性和意想不到的触感，使界面令人难忘和愉快。将功能提升到令人愉悦。用于添加润色、个性、动画、微交互、乐趣或让界面感觉有趣和令人难忘',
        'design-consultation': '设计咨询：了解你的产品，研究行业格局，提出完整的设计系统（美学、排版、颜色、布局、间距、运动），并生成字体+颜色预览页面。创建 DESIGN.md 作为项目设计的事实来源',
        'design-review': '设计师视角 QA：发现视觉不一致、间距问题、层次问题、AI slop 模式和缓慢的交互——然后修复它们。迭代修复源代码中的问题。用于"审计设计"、"视觉 QA"、"检查它看起来是否好"或"设计润色"',
        'dispatching-parallel-agents': '当面临 2 个或更多可以无共享状态或顺序依赖地处理的独立任务时使用',
        'distill': '通过移除不必要的复杂性将设计剥离到本质。伟大的设计是简单、强大和干净的。用于简化、整理、减少噪音、移除元素或让 UI 更干净和专注',
        'document-release': '发布后文档更新。读取所有项目文档，交叉引用差异，更新 README/ARCHITECTURE/CONTRIBUTING/CLAUDE.md 以匹配已发布内容，润色 CHANGELOG 语气，清理 TODO，并可选地更新 VERSION',
        'executing-plans': '当你有书面实施计划要在单独的会话中执行并带有审查检查点时使用',
        'extract': '提取和整合可复用组件、设计令牌和模式到你的设计系统。识别系统化复用的机会并丰富你的组件库',
        'find-skills': '帮助用户发现和安装 agent skills。当用户问"如何做 X"、"为 X 找一个 skill"、"有没有一个 skill 可以..."时使用',
        'finishing-a-development-branch': '当实施完成、所有测试通过，并且你需要决定如何集成工作时使用——指导通过提供合并、PR 或清理的结构化选项来完成开发工作',
        'fix-issue': '当用户要求修复 bug、回归、失败行为、损坏的功能、运行时错误或重复错误模式时使用。特别关注：用户提供错误日志、堆栈跟踪、控制台输出、构建失败、运行时异常或错误截图。触发词："修复这个"、"调试这个"、"找到根本原因"',
        'freeze': '将文件编辑限制到会话的特定目录。阻止在允许路径之外进行编辑和写入。用于调试以防止意外"修复"无关代码，或当你希望将更改范围限制在一个模块时',
        'gstack-upgrade': '将 gstack 升级到最新版本。检测全局与 vendor 安装，运行升级并显示新功能。用于"upgrade gstack"、"update gstack"、"get latest version"',
        'guard': '完整安全模式：破坏性命令警告 + 目录范围编辑。结合 /careful 和 /freeze 以在触碰生产环境或调试实时系统时提供最大安全性',
        'impeccable': '创建独特、生产级前端界面，具有高设计质量。生成富有创意、精美的代码，避免通用的 AI 美学。使用 craft 进行形状-然后构建，teach 进行设计上下文设置，或 extract 将可复用组件和令牌提取到设计系统',
        'investigate': '系统性调试，进行根本原因调查。四个阶段：调查、分析、假设、实施。铁律：没有根本原因就没有修复。用于"debug this"、"fix this bug"、"why is this broken"、"investigate this error"',
        'land-and-deploy': 'Landing 和部署工作流。合并 PR，等待 CI 和部署，通过金丝雀检查验证生产健康。在 /ship 创建 PR 后接管。用于"merge"、"land"、"deploy"、"merge and verify"、"land it"、"ship it to production"',
        'layout': '改善布局、间距和视觉节奏。修复单调的网格、不一致的间距和薄弱的视觉层次。用于布局感觉不对、间距问题、视觉层次、拥挤的 UI、对齐问题或想要更好的构图',
        'normalize': '审计并将 UI 重新对齐到设计系统标准、间距、令牌和模式。用于一致性、设计漂移、不匹配的风格、令牌或希望将功能重新纳入系统',
        'office-hours': 'YC Office Hours——两种模式。创业模式：六个强制问题暴露需求现实、现状、绝望的特异性、最窄的楔子、观察和未来适配。构建者模式：设计思考头脑风暴。保存设计文档',
        'onboard': '设计和改进 onboarding 流程、空状态和首次运行体验，以帮助用户快速获得价值。用于 onboarding、首次用户、空状态、激活、入门或新用户流程',
        'optimize': '诊断并修复 UI 性能，涵盖加载速度、渲染、动画、图像和包大小。用于缓慢、卡顿、性能、包大小、加载时间或想要更快、更流畅的体验',
        'overdrive': '用技术上雄心勃勃的实现——着色器、弹簧物理、滚动驱动揭示、60fps 动画——将界面推向传统极限之外。用于想要惊艳、印象深刻、全力以赴或感觉非凡的事物',
        'plan-ceo-review': 'CEO/创始人模式计划审查。重新思考问题，找到 10 星产品，挑战前提，在创造更好产品时扩展范围。四种模式：范围扩展、选择性扩展、保持范围、范围缩减。用于"think bigger"、"expand scope"、"strategy review"',
        'plan-design-review': '设计师视角计划审查——交互式，类似 CEO 和工程审查。为每个设计维度评分 0-10，解释如何达到 10，然后修复计划以实现。在计划模式下工作。用于"review the design plan"或"design critique"',
        'plan-eng-review': '工程经理模式计划审查。锁定执行计划——架构、数据流、图表、边缘情况、测试覆盖、性能。以有见地的推荐交互式地遍历问题。用于"review the architecture"、"engineering review"、"lock in the plan"',
        'planning-with-files': '实现 Manus 风格的基于文件的规划，以组织和跟踪复杂任务的进度。创建 task_plan.md、findings.md 和 progress.md。用于被要求计划、分解或组织多步骤项目、研究任务或任何需要 >5 个工具调用的工作',
        'polish': '执行最终质量检查，修复对齐、间距、一致性和微观细节问题，然后再发布。用于润色、收尾、发布前审查、某些东西看起来不对或想要从好到伟大',
        'quieter': '降低视觉上过于激进或过度刺激的设计，在保持质量的同时减少强度。用于太大胆、太响亮、压倒性、激进、花哨或想要更平静、更精致的美学',
        'receiving-code-review': '在实现建议之前接收代码审查反馈时使用，特别是当反馈看起来不清楚或技术上值得怀疑时——需要技术严谨性和验证，而不是表演性同意或盲目实施',
        'requesting-code-review': '在完成任务、实施主要功能或合并之前验证工作是否符合要求时使用',
        'restore-conversation': 'DEPRECATED — use Reactivate for Canon task page based resume.',
        'retro': '每周工程回顾。分析提交历史、工作模式和代码质量指标，带有持久历史和趋势跟踪。团队感知：分解个人贡献，表扬和成长领域。用于"weekly retro"、"what did we ship"',
        'review': '着陆前 PR 审查。分析相对于基础分支的差异，检查 SQL 安全性、LLM 信任边界违规、条件副作用和其他结构问题。用于"review this PR"、"code review"、"pre-landing review"',
        'save-conversation': 'DEPRECATED — use Secure for Canon task page updates.',
        'scaffold': 'DEPRECATED — AGENTS.md by convention, Canon for project pages.',
        'setup-browser-cookies': '从真实 Chromium 浏览器导入 cookies 到 headless browse 会话。打开交互式选择器 UI，选择要导入的 cookie 域。用于 QA 测试已认证页面之前',
        'setup-deploy': '为 /land-and-deploy 配置部署设置。检测你的部署平台（Fly.io、Render、Vercel、Netlify、Heroku、GitHub Actions、自定义）、生产 URL、健康检查端点和部署状态命令',
        'shape': '在编写代码之前规划功能的 UX 和 UI。运行结构化的发现访谈，然后生成指导实施的设计简报。在规划阶段使用以建立设计方向、约束和策略',
        'ship': 'Ship 工作流：检测 + 合并基础分支、运行测试、审查差异、更新 VERSION、更新 CHANGELOG、提交、推送、创建 PR。用于"ship"、"deploy"、"push to main"、"create a PR"',
        'subagent-driven-development': '在当前会话中执行具有独立任务的实施计划时使用',
        'systematic-debugging': '在遇到任何 bug、测试失败或意外行为之前使用',
        'task-report-slides': '在工作完成后创建以任务为中心的 HTML 演示文稿。当用户明确要求生成报告、回顾、演示文稿、幻灯片或摘要文档时使用',
        'test-driven-development': '在编写任何实现代码之前实施任何功能或 bug 修复时使用',
        'unfreeze': '清除由 /freeze 设置的 freeze 边界，允许再次编辑所有目录。用于"unfreeze"、"unlock edits"、"remove freeze"、"allow all edits"',
        'using-git-worktrees': '在开始需要与当前工作区隔离的功能工作之前或执行实施计划之前使用——创建隔离的 git worktree',
        'using-superpowers': '在每次对话开始时使用——建立如何查找和使用技能',
        'verification-before-completion': '在声称工作完成、修复或通过之前，在提交或创建 PR 之前使用——需要运行验证命令并确认输出',
        'writing-plans': '当你有规范或需求用于多步骤任务时使用',
        'writing-skills': '在创建新技能、编辑现有技能或部署前验证技能时使用',
        'harden': '强化代码和设计，增加安全性和健壮性',
    }

    # upstream 颜色映射
    UPSTREAM_COLORS = {
        'gstack': '#8b5cf6',
        'anthropics': '#d97757',
        'superpowers': '#3b82f6',
        'planning-with-files': '#10b981',
        'agent-skills': '#141413',
        'impeccable': '#e11d48',
        'local': '#b0aea5',
        'marketplace': '#d97757',
    }

    # 位于 ~/.agents/skills 或 ~/.claude/skills 下的真实目录（非 symlink），
    # 属于 impeccable 设计技能套件
    IMPECCABLE_SKILLS = {
        'adapt', 'animate', 'arrange', 'audit', 'bolder', 'clarify', 'colorize',
        'critique', 'delight', 'distill', 'extract', 'harden', 'impeccable',
        'layout', 'normalize', 'onboard', 'optimize', 'overdrive', 'polish',
        'quieter', 'shape', 'typeset'
    }

    def __init__(self, skill_dirs=None, lang='zh'):
        self.lang = lang
        self.skill_dirs = skill_dirs or self._default_skill_dirs()

    def _default_skill_dirs(self) -> List[Tuple[Path, str]]:
        """默认扫描目录。通用 agent 优先，再扫描特定 agent runtime"""
        dirs = []
        # 通用 agent skills
        agents_dir = Path.home() / ".agents" / "skills"
        if agents_dir.exists():
            dirs.append((agents_dir, "agent"))
        # 特定 agent runtimes
        runtime_paths = {
            "claude": ".claude/skills",
            "codex": ".codex/skills",
            "kimi": ".kimi/skills",
            "pi": ".pi/agent/skills",
            "hermes": ".hermes/skills",
        }
        for runtime, rel_path in runtime_paths.items():
            rdir = Path.home() / rel_path
            if rdir.exists():
                dirs.append((rdir, runtime))
        # marketplace
        marketplace_dir = Path.home() / ".claude" / "plugins" / "marketplaces" / "anthropic-agent-skills" / "skills"
        if marketplace_dir.exists():
            dirs.append((marketplace_dir, "marketplace"))
        return dirs

    def _infer_upstream(self, skill_path: str) -> str:
        """从真实路径推断 upstream 仓库名"""
        real = os.path.realpath(skill_path)
        name = Path(skill_path).name

        # 显式 impeccable 技能套件
        if name in self.IMPECCABLE_SKILLS:
            return 'impeccable'

        # 标准化路径分隔符
        real = real.replace('\\', '/')
        lower = real.lower()

        # 从 upstream 快照目录推断
        if '/upstream/' in lower:
            parts = real.split('/')
            try:
                idx = parts.index('upstream')
                repo_dir = parts[idx + 1] if idx + 1 < len(parts) else ''
                # 去掉 -repo / -skills 后缀
                repo = re.sub(r'-(repo|skills?)$', '', repo_dir, flags=re.IGNORECASE)
                return repo if repo else 'upstream'
            except ValueError:
                pass

        # 从 ~/.agents/repos/agent-skills 推断
        if '/.agents/repos/agent-skills/' in lower:
            return 'agent-skills'

        # marketplace
        if '/marketplaces/' in lower or '/anthropic-agent-skills/' in lower:
            return 'marketplace'

        return 'local'

    def scan_all(self) -> List[SkillInfo]:
        """扫描所有 skills，按名称去重（先扫描的优先）"""
        seen: Set[str] = set()
        all_skills = []

        for directory, source in self.skill_dirs:
            if not directory.exists():
                continue
            for item in directory.iterdir():
                if not item.is_dir() or item.name.startswith('.'):
                    continue
                if item.name in seen:
                    continue
                skill_md = item / "SKILL.md"
                if skill_md.exists():
                    info = self._parse_skill_md(skill_md, source=source, skill_dir=item)
                    if info:
                        all_skills.append(info)
                        seen.add(item.name)

        return all_skills

    def _parse_skill_md(self, md_path: Path, source: str, skill_dir: Path) -> Optional[SkillInfo]:
        """解析 SKILL.md 文件"""
        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()

            frontmatter = self._extract_frontmatter(content)
            if not frontmatter:
                return None

            name = frontmatter.get('name', md_path.parent.name)
            description = frontmatter.get('description', '')
            if isinstance(description, list):
                description = ' '.join(description)
            description = description.strip().strip('"').strip("'")

            if self.lang == 'zh' and name in self.DESCRIPTIONS_ZH:
                description = self.DESCRIPTIONS_ZH[name]

            upstream = self._infer_upstream(str(skill_dir))

            return SkillInfo(
                name=name,
                description=description,
                path=str(md_path.parent),
                source=source,
                upstream=upstream
            )
        except Exception as e:
            print(f"Warning: Failed to parse {md_path}: {e}")
            return None

    def _extract_frontmatter(self, content: str) -> Optional[Dict]:
        """提取 YAML frontmatter，支持多行值"""
        match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not match:
            return None
        try:
            return yaml.safe_load(match.group(1)) or {}
        except Exception:
            return self._fallback_parse_frontmatter(match.group(1))

    def _fallback_parse_frontmatter(self, text: str) -> Dict:
        """非标准 YAML frontmatter 的回退解析"""
        result = {}
        lines = text.split('\n')
        current_key = None
        current_value = []
        for line in lines:
            stripped = line.rstrip()
            if not stripped:
                continue
            if current_key and not line.startswith(' ') and not line.startswith('\t'):
                if ':' in stripped:
                    result[current_key] = '\n'.join(current_value).strip()
                    current_key = None
                    current_value = []
                else:
                    current_value.append(stripped)
                    continue
            if current_key is None:
                if ':' not in stripped:
                    continue
                key, val = stripped.split(':', 1)
                key = key.strip()
                val = val.strip()
                if val == '|':
                    current_key = key
                    current_value = []
                else:
                    result[key] = val.strip('"').strip("'")
            else:
                current_value.append(stripped)
        if current_key and current_value:
            result[current_key] = '\n'.join(current_value).strip()
        return result


class SkillsClassifier:
    """对 skills 进行分类"""

    DOC_KEYWORDS = ['pdf', 'docx', 'ppt', 'pptx', 'xlsx', 'xls', 'document', 'formula', 'katex',
                    'word', 'excel', 'powerpoint', 'spreadsheet']

    DESIGN_KEYWORDS = ['art', 'design', 'canvas', 'frontend', 'web', 'theme', 'gif', 'slack',
                       'brand', 'algorithmic', 'visual', 'animate', 'animation', 'motion',
                       'colorize', 'bolder', 'quieter', 'polish', 'delight', 'overdrive',
                       'layout', 'arrange', 'distill', 'impeccable', 'shape']

    CODE_KEYWORDS = ['mcp', 'testing', 'test', 'skill-creator', 'developer', 'build', 'code',
                     'debug', 'deploy', 'ship', 'qa', 'review', 'security', 'cso', 'audit',
                     'performance', 'optimize', 'benchmark', 'fix', 'investigate', 'guard',
                     'careful', 'freeze', 'unfreeze', 'git', 'worktree', 'plan', 'retro',
                     'scaffold', 'setup', 'verify', 'systematic', 'subagent',
                     'executing', 'writing', 'extract', 'normalize', 'autoplan', 'codex']

    COMM_KEYWORDS = ['communication', 'comms', 'internal', 'doc-coauthoring', 'proposal',
                     'report', 'conversation', 'save', 'restore', 'office-hours', 'onboard',
                     'brainstorming', 'clarify', 'critique', 'design-consultation',
                     'design-review', 'plan-ceo-review', 'plan-eng-review', 'plan-design-review',
                     'receiving-code-review', 'requesting-code-review', 'land-and-deploy',
                     'document-release', 'task-report', 'canary', 'browse']

    def classify(self, skill: SkillInfo) -> str:
        """分类 skill"""
        name_lower = skill.name.lower()
        desc_lower = skill.description.lower()
        text = f"{name_lower} {desc_lower}"

        if any(kw in text for kw in self.DOC_KEYWORDS):
            return 'doc'
        elif any(kw in text for kw in self.DESIGN_KEYWORDS):
            return 'design'
        elif any(kw in text for kw in self.CODE_KEYWORDS):
            return 'code'
        elif any(kw in text for kw in self.COMM_KEYWORDS):
            return 'comm'
        else:
            return 'code'


class CheatsheetGenerator:
    """生成 HTML 速查表"""

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
            'name': '沟通与协作',
            'color': '#b0aea5',
            'gradient': 'linear-gradient(135deg, #b0aea5, #a2a097)'
        }
    }

    ICONS = {
        'doc': {'pdf': 'PDF', 'docx': 'DOC', 'pptx': 'PPT', 'xlsx': 'XLS', 'katex': '公式'},
        'design': {'algorithmic-art': '生成', 'canvas-design': '画布', 'frontend-design': '前端',
                   'web-artifacts-builder': 'Web', 'theme-factory': '主题', 'slack-gif-creator': '动图',
                   'brand-guidelines': '品牌', 'animate': '动画', 'shape': '塑形'},
        'code': {'mcp-builder': 'MCP', 'webapp-testing': '测试', 'skill-creator': '技能',
                 'qa': 'QA', 'ship': 'SHIP', 'codex': 'CODEX', 'cso': 'CSO', 'fix-issue': 'FIX',
                 'investigate': 'DEBUG', 'guard': 'GUARD'},
        'comm': {'doc-coauthoring': '文档', 'internal-comms': '沟通', 'Secure': 'SAVE',
                 'Reactivate': 'RESTORE', 'office-hours': 'YC', 'onboard': 'ONB',
                 'design-review': 'REV', 'plan-ceo-review': 'CEO', 'plan-eng-review': 'ENG',
                 'plan-design-review': 'DSGN'}
    }

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
        'skill-cheatsheet': '生成技能速查表、更新cheatsheet、查看已安装技能',
        'qa': 'qa、test this site、find bugs、test and fix',
        'ship': 'ship、deploy、push to main、create a PR',
        'plan-ceo-review': 'think bigger、expand scope、strategy review',
        'plan-eng-review': 'review architecture、engineering review、lock in plan',
        'plan-design-review': 'review design plan、design critique',
        'fix-issue': 'fix this、debug this、root cause',
        'investigate': 'debug this、fix this bug、root cause analysis',
        'cso': 'security audit、threat model、vulnerability scan',
        'Secure': 'save conversation、store context、write recap',
        'Reactivate': 'restore conversation、recover context、resume',
        'codex': 'codex review、codex challenge、ask codex',
        'browse': 'open in browser、test the site、take screenshot',
        'canary': 'monitor deploy、canary、post-deploy check',
        'guard': 'guard mode、full safety、maximum safety',
        'autoplan': 'auto review、autoplan、run all reviews',
        'audit': 'accessibility check、performance audit、technical quality',
        'document-release': 'update docs、sync documentation、post-ship docs',
    }

    def __init__(self, lang='zh'):
        self.lang = lang
        self.classifier = SkillsClassifier()

    UPSTREAM_SECTIONS = {
        'gstack': {'name': 'gstack', 'color': '#8b5cf6'},
        'anthropics': {'name': 'anthropics', 'color': '#d97757'},
        'superpowers': {'name': 'superpowers', 'color': '#3b82f6'},
        'impeccable': {'name': 'impeccable', 'color': '#e11d48'},
        'planning-with-files': {'name': 'planning-with-files', 'color': '#10b981'},
        'agent-skills': {'name': 'agent-skills', 'color': '#141413'},
        'marketplace': {'name': 'marketplace', 'color': '#d97757'},
        'local': {'name': 'local / other', 'color': '#b0aea5'},
    }

    def get_icon(self, skill: SkillInfo, category: str) -> str:
        """获取技能图标文字"""
        icon = self.ICONS.get(category, {}).get(skill.name, '')
        if icon:
            return icon
        if skill.source == 'marketplace':
            return 'MKT'
        return skill.name[:4].upper()

    def get_trigger_hint(self, skill: SkillInfo) -> str:
        """获取触发词提示"""
        hint = self.TRIGGER_HINTS.get(skill.name, '')
        if self.lang == 'zh':
            return f"触发词：{hint}" if hint else ""
        return f"Trigger: {hint}" if hint else ""

    def get_upstream_color(self, upstream: str) -> str:
        """获取 upstream 对应颜色"""
        return SkillsScanner.UPSTREAM_COLORS.get(upstream, '#b0aea5')

    def get_source_badge(self, skill: SkillInfo) -> str:
        """获取来源 badge HTML（优先显示 upstream）"""
        is_zh = self.lang == 'zh'
        upstream = skill.upstream
        source = skill.source

        badges = []

        # upstream badge（always show if known and not local）
        if upstream and upstream != 'local':
            color = self.get_upstream_color(upstream)
            text = upstream.upper()
            if is_zh:
                text = {
                    'gstack': 'gstack',
                    'anthropics': 'anthropics',
                    'superpowers': 'superpowers',
                    'planning-with-files': 'planning',
                    'agent-skills': 'agent-skills',
                    'marketplace': '官方',
                }.get(upstream, upstream)
            badges.append(f'<span class="badge upstream-badge" style="background: {color}; color: #fff;">{text}</span>')

        # runtime badge（仅当不是通用 agent 或 upstream 为 local 时显示）
        if source != 'agent' or upstream == 'local':
            runtime_labels = {
                'agent': 'AGENT',
                'claude': 'CLAUDE',
                'codex': 'CODEX',
                'kimi': 'KIMI',
                'pi': 'PI',
                'hermes': 'HERMES',
                'marketplace': 'MKT',
            }
            text = runtime_labels.get(source, source.upper())
            if is_zh and source == 'marketplace':
                text = '官方'
            badges.append(f'<span class="badge badge-runtime">{text}</span>')

        return ''.join(badges)

    def generate(self, skills: List[SkillInfo], output_path: Path) -> str:
        """生成 HTML（两种视图合并到一个可切换的页面中）"""
        html = self._render_html_unified(skills, len(skills))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        return str(output_path)

    def _render_html_unified(self, skills: List[SkillInfo], total_count: int) -> str:
        """渲染统一 HTML，包含两种视图和切换按钮"""
        is_zh = self.lang == 'zh'

        # 按分类分组
        categorized = {cat: [] for cat in self.CATEGORIES}
        for skill in skills:
            cat = self.classifier.classify(skill)
            categorized[cat].append(skill)

        # 按发布商分组
        grouped: Dict[str, List[SkillInfo]] = {}
        for skill in skills:
            grouped.setdefault(skill.upstream, []).append(skill)
        order = ['gstack', 'anthropics', 'superpowers', 'impeccable', 'planning-with-files', 'agent-skills', 'marketplace', 'local']
        sorted_keys = [k for k in order if k in grouped] + [k for k in grouped if k not in order]

        # 构建分类视图内容
        category_html = ""
        for cat, cat_info in self.CATEGORIES.items():
            sec_skills = categorized.get(cat, [])
            if not sec_skills:
                continue
            category_html += f"""
        <div class="section">
            <div class="section-title">{cat_info['name']}</div>
            <div class="grid">
"""
            for skill in sec_skills:
                category_html += self._render_skill_card(skill, cat)
            category_html += """
            </div>
        </div>
"""

        # 构建发布商视图内容
        publisher_html = ""
        for key in sorted_keys:
            sec_info = self.UPSTREAM_SECTIONS.get(key, {'name': key, 'color': '#b0aea5'})
            color = sec_info['color']
            sec_skills = grouped[key]
            publisher_html += f"""
        <div class="section">
            <div class="section-title" style="color: {color};">
                <span style="background: {color}; width: 8px; height: 8px; border-radius: 50%; display: inline-block;"></span>
                {sec_info['name']} <span style="color: #b0aea5; font-weight: 400; font-size: 14px;">({len(sec_skills)})</span>
            </div>
            <div class="grid">
"""
            for skill in sec_skills:
                cat = self.classifier.classify(skill)
                publisher_html += self._render_skill_card(skill, cat)
            publisher_html += """
            </div>
        </div>
"""

        cat_legend = [
            ('#d97757', '文档处理' if is_zh else 'Documents'),
            ('#6a9bcc', '设计创意' if is_zh else 'Design'),
            ('#788c5d', '开发工具' if is_zh else 'Development'),
            ('#b0aea5', '沟通协作' if is_zh else 'Communication'),
            ('#8b5cf6', 'gstack'),
            ('#3b82f6', 'superpowers'),
            ('#10b981', 'planning-with-files'),
            ('#141413', 'agent-skills'),
        ]
        pub_legend = [
            ('#d97757', 'anthropics'),
            ('#8b5cf6', 'gstack'),
            ('#3b82f6', 'superpowers'),
            ('#10b981', 'planning-with-files'),
            ('#141413', 'agent-skills'),
            ('#d97757', 'marketplace' if not is_zh else '官方'),
            ('#b0aea5', 'local / other'),
        ]

        tab_cat = '功能分类' if is_zh else 'By Category'
        tab_pub = '发布商' if is_zh else 'By Publisher'

        html = f"""<!DOCTYPE html>
<html lang="{'zh-CN' if is_zh else 'en'}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Coding Agent Skills {'速查表' if is_zh else 'Cheatsheet'}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family={'Noto+Sans+SC:wght@400;500;600;700&Noto+Serif+SC:wght@400;500;600' if is_zh else 'Poppins:wght@400;500;600;700&family=Lora:wght@400;500;600'}&display=swap');

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
            margin-bottom: 24px;
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

        .tabs {{
            display: flex;
            justify-content: center;
            gap: 8px;
            margin-bottom: 32px;
        }}

        .tab {{
            font-family: {'Noto Sans SC, PingFang SC' if is_zh else 'Poppins, Arial'}, sans-serif;
            font-size: 14px;
            font-weight: 500;
            padding: 8px 20px;
            border-radius: 20px;
            border: 1px solid #e8e6dc;
            background: white;
            color: #5c5a54;
            cursor: pointer;
            transition: all 0.2s ease;
        }}

        .tab:hover {{
            border-color: #d97757;
            color: #d97757;
        }}

        .tab.active {{
            background: #141413;
            color: #faf9f5;
            border-color: #141413;
        }}

        .view {{ display: none; }}
        .view.active {{ display: block; }}

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
        }}

        .badge-runtime {{ background: #b0aea5; color: #faf9f5; }}

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
            <div class="subtitle">Coding Agent</div>
            <h1>Skills {'速查表' if is_zh else 'Cheatsheet'}</h1>
            <p style="color: #b0aea5; font-size: 15px;">{'所有已安装技能的快速参考指南' if is_zh else 'Quick reference guide for all installed skills'}</p>
        </header>

        <div class="tabs">
            <button class="tab active" onclick="switchView('category')">{tab_cat}</button>
            <button class="tab" onclick="switchView('publisher')">{tab_pub}</button>
        </div>

        <div id="view-category" class="view active">
{category_html}
{self._render_footer(cat_legend, total_count)}
        </div>

        <div id="view-publisher" class="view">
{publisher_html}
{self._render_footer(pub_legend, total_count)}
        </div>
    </div>

    <script>
        function switchView(viewName) {{
            document.querySelectorAll('.view').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
            document.getElementById('view-' + viewName).classList.add('active');
            event.target.classList.add('active');
        }}
    </script>
</body>
</html>
"""
        return html

    def _render_footer(self, legend_items, total_count) -> str:
        is_zh = self.lang == 'zh'
        html = """
        <footer>
            <div class="legend">
"""
        for color, label in legend_items:
            html += f'<div class="legend-item"><div class="legend-dot" style="background: {color};"></div> {label}</div>\n'

        html += f"""
            </div>
            <p class="footer-text">Coding Agent {'技能速查表' if is_zh else 'Skills Cheatsheet'} • {total_count} {'个技能已安装' if is_zh else 'skills installed'}</p>
        </footer>
"""
        return html

    def _render_skill_card(self, skill: SkillInfo, category: str) -> str:
        """渲染单个 skill 卡片"""
        is_zh = self.lang == 'zh'
        icon = self.get_icon(skill, category)
        badge = self.get_source_badge(skill)
        trigger_hint = self.get_trigger_hint(skill)
        keywords = self._extract_keywords(skill.description, is_zh)

        return f"""
                <div class="skill-card">
                    <div class="skill-header">
                        <div class="skill-icon {category}">{icon}</div>
                        <div class="skill-name">{skill.name}{badge}</div>
                    </div>
                    <div class="skill-desc">{skill.description}</div>
                    <div class="skill-keywords">
                        {keywords}
                    </div>
                    {f'<div class="trigger-hint">{trigger_hint}</div>' if trigger_hint else ''}
                </div>"""

    def _extract_keywords(self, description: str, is_zh: bool) -> str:
        """从描述中提取关键词"""
        keywords = []
        common_patterns = [
            r'(PDF|Word|Excel|PowerPoint|PPT|DOCX|XLSX)',
            r'(React|Vue|HTML|CSS|Tailwind)',
            r'(API|MCP|REST)',
            r'(p5\.js|Playwright)',
            r'(文档|表格|幻灯片|公式|图表)',
            r'(QA|PR|CI/CD|Git|Deploy|Ship)',
            r'(安全|审计|测试|调试|review)',
        ]

        for pattern in common_patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            keywords.extend(matches[:2])

        keywords = keywords[:4]
        return ''.join(f'<span class="keyword">{kw}</span>' for kw in keywords)


def generate(
    output=None,
    lang='zh',
    skill_dirs=None,
    open_browser=True
):
    """
    生成 Skills 速查表（单 HTML 双视图：功能分类 + 发布商分组）

    Args:
        output: 输出文件路径，默认 /media/yhr/2T/Canon/artifacts/generated/skills-cheatsheet.html
        lang: 语言，'zh' 或 'en'
        skill_dirs: 额外的 skills 目录列表（格式 path:source）
        open_browser: 是否自动打开浏览器

    Returns:
        生成的文件路径
    """
    output_path = Path(output) if output else DEFAULT_OUTPUT_PATH

    extra_dirs = []
    if skill_dirs:
        for item in skill_dirs:
            if ':' in item:
                path, source = item.rsplit(':', 1)
                extra_dirs.append((Path(path), source))
            else:
                extra_dirs.append((Path(item), 'local'))

    scanner = SkillsScanner(lang=lang)
    if extra_dirs:
        scanner.skill_dirs = extra_dirs + scanner.skill_dirs

    skills = scanner.scan_all()
    skills.sort(key=lambda s: s.name.lower())

    generator = CheatsheetGenerator(lang=lang)
    result_path = generator.generate(skills, output_path)

    print(f"✅ Generated: {result_path}")
    print(f"   Found {len(skills)} skills")

    if open_browser:
        try:
            webbrowser.open(f"file://{result_path}")
        except Exception:
            pass

    return result_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Coding Agent Skills Cheatsheet")
    parser.add_argument('-o', '--output', help='Output file path')
    parser.add_argument('-lang', '--lang', default='zh', choices=['zh', 'en'], help='Language')
    parser.add_argument('-d', '--skill-dir', action='append', help='Additional skill directory (path:source)')
    parser.add_argument('--no-open', action='store_true', help='Do not open browser')

    args = parser.parse_args()

    generate(
        output=args.output,
        lang=args.lang,
        skill_dirs=args.skill_dir,
        open_browser=not args.no_open
    )
