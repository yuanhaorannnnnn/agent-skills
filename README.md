# agent-skills

19 个跨 agent runtime 的通用 skill，覆盖开发全流程——从方案设计、代码审查、深度研究到收尾提交、周报生成。一次安装，6 个 runtime 同步。

## 安装

```bash
git clone https://github.com/yuanhaorannnnnn/agent-skills.git ~/.agents/repos/agent-skills
bash ~/.agents/repos/agent-skills/scripts/install.sh
```

安装后 `~/.agents/skills`、`~/.claude/skills`、`~/.codex/skills`、`~/.kimi/skills`、`~/.pi/agent/skills`、`~/.hermes/skills` 全部自动创建符号链接。

后续 `git pull` 后运行 `node scripts/install.mjs install` 即可增量同步，或者靠仓库自带的 `post-commit` hook 自动触发。

## 全部 skill（19 个）

### 开发流程

| Skill | 用途 | 触发方式 |
|------|------|---------|
| `dev-design` | 生成面向产品/测试/开发的 14 节技术方案文档 | "生成开发方案"、"写设计评审文档" |
| `dev-wrapup` | 开发完成后 git commit + push + save conversation + 更新 planning | "开发完成了"、"wrap up"、"提交并保存" |
| `code-reviewer` | 审查 diff，检查正确性、回归、安全、可维护性 | "review 一下"、"code review" |
| `fix-issue` | 根据报错日志定位根因并修复 | "fix this"、"debug this" |

### 研究与规划

| Skill | 用途 | 触发方式 |
|------|------|---------|
| `deep-research` | 基于本地代码的三阶段结构化深度研究 | "帮我调研一下"、"deep dive into" |
| `plan-workspace` | 创建 conversation-scoped 规划工作区（spec/task_plan/findings/progress） | 复杂任务开始时 |
| `report` | 生成学术论文结构的 Markdown 技术报告 | "生成技术报告"、"写个总结" |
| `autoresearch-loop` | 编译→基准→分析→改进的自动化优化循环 | "自动优化"、"run experiments" |

### 会话管理

| Skill | 用途 | 触发方式 |
|------|------|---------|
| `restore-conversation` | 恢复上次对话现场 | "restore conversation"、"接着上次继续" |
| `save-conversation` | 保存当前对话上下文 | "save conversation"、"记住进度" |
| `capture-mistake-rule` | 将错误经验记录为防错规则 | "记住这个错误"、"add a guardrail" |

### 自动化与工具

| Skill | 用途 | 触发方式 |
|------|------|---------|
| `work-report` | 从 agent 对话自动生成周报/月报（支持主题过滤） | "周报"、"月报"、"work report" |
| `scaffold` | 初始化仓库的 agent system 布局（AGENTS.md + .agent-state + .planning） | "初始化 agent system"、"bootstrap repo" |
| `skill-cheatsheet` | 生成所有已安装 skill 的 HTML 速查表 | "生成技能速查表"、"skills list" |
| `skill-architect` | 将一组 skill 可视化：协作关系、信息流、层次结构（PNG/HTML/ASCII） | "架一下这几个 skill"、"skill 关系图" |
| `skill-map` | 扫描所有 runtime 的已安装 skill，生成可视化地图 | "我有哪些技能"、"列出技能" |
| `skill-evaluator` | 评估新功能是否需要创建 skill，防止技能膨胀 | "这个要不要封装成 skill" |
| `skill-status` | 查询 skill 在各来源的启用/禁用状态 | "哪些 skill 被禁用了" |
| `video-ingest` | 下载 X/Twitter/小红书/B站/YouTube 视频，准备字幕/笔记工作流 | "下载视频"、"video ingest" |

## CLI

```bash
node scripts/install.mjs install    # 安装全部启用 skill 到 6 个 runtime
node scripts/install.mjs doctor     # 检查所有符号链接和 SKILL.md 完整性
node scripts/install.mjs list       # 按类别列出已发布 skill
node scripts/install.mjs update     # git pull + install
```

## 运行时覆盖

每个 skill 同时安装到以下 6 个目录：

```
~/.agents/skills/      ~/.claude/skills/      ~/.codex/skills/
~/.kimi/skills/        ~/.pi/agent/skills/    ~/.hermes/skills/
```

## 特性

- **post-commit 自动同步**：每次 commit 后自动运行 `install.mjs install`，新建 skill 不会漏装
- **禁用控制**：`manifest.yaml` 中 `enabled: false` 的 skill 不会安装到任何 runtime
- **第三方上游管理**：通过 `agent-platform` 同步、审核并选择性启用外部 skill 仓库，配置在 `state/disabled-upstreams.yaml`

## 目录结构

```
skills/<skill-name>/
├── SKILL.md            # skill 定义（frontmatter + 工作流）
├── references/         # 参考文档（可选）
│   └── taste.md        #   如：写作风格反例对照
├── scripts/            # 可执行脚本（可选）
├── evals/              # 触发评测用例（可选）
│   └── evals.json
└── templates/          # 模板文件（可选）
scripts/
├── install.mjs         # 跨 runtime 符号链接安装器
├── install.sh          # 安装入口
├── update.sh           # git pull + reinstall
├── restore_conversation.py
├── save_conversation.py
└── ...
manifest.yaml           # skill 注册表（name / enabled / category）
```
