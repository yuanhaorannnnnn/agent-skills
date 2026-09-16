# agent-skills

`agent-skills` 是一个面向编码 agent 的可复用 skill 仓库，用统一 manifest 管理开发、调试、研究、文档、自动化与交付工作流。仓库当前包含 20 个已启用 skill；`manifest.yaml` 是名称、启用状态、类别、调用方式和依赖关系的事实来源，并与 20 个 `skills/*/SKILL.md` 目录一一对应。

项目重点是让维护者能够审阅、测试和分发同一组工作流，而不是把 skill 绑定到单个 agent 产品。当前安装器支持 Agents 通用目录与 Claude Code，通过符号链接保留单一源码。

## 核心特性

- **声明式注册表**：`manifest.yaml` 记录每个 skill 的 `enabled`、`category`、`invocation`、`role` 和 `calls`。
- **可组合工作流**：覆盖需求执行、缺陷修复、review、研究、文档生成、自动化调优与任务收尾。
- **本地分发**：安装器将启用的 skill 链接到 `~/.agents/skills` 和 `~/.claude/skills`，不会改动其他来源的符号链接。
- **可验证契约**：doctor、metadata/contract tests 和各 skill gate 检查目录、引用、调用边界及工作流状态。
- **安全边界**：高风险工作流把确认、验证和外部状态变更写成显式 gate，而不是默认自动执行。

## 安装

要求 Node.js 18+；运行 Python 测试时还需要 Python 3 和 PyYAML。

```bash
git clone https://github.com/yuanhaorannnnnn/agent-skills.git ~/.agents/repos/agent-skills
cd ~/.agents/repos/agent-skills
npm ci
bash scripts/install.sh
```

安装会为所有已启用 skill 和共享 `.scripts` 创建符号链接：

```text
~/.agents/skills/
~/.claude/skills/
```

后续更新：

```bash
node scripts/install.mjs update
```

该命令执行 `git pull --ff-only` 后重新安装。若工作树包含本地修改，请先自行处理，避免更新失败。

## 使用与验证

```bash
node scripts/install.mjs list       # 按类别列出已启用 skill
node scripts/install.mjs install    # 刷新两个 runtime 的符号链接
node scripts/install.mjs doctor     # 检查 manifest、skill 文件和已安装链接

python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m unittest discover -s skills/acquisition/tests -p 'test_*.py'
python3 -m unittest discover -s skills/passdown/tests -p 'test_*.py'
```

## Skill 目录

| Skill | Category | Invocation | Role |
|---|---|---|---|
| `acquisition` | media | user | adapter |
| `after-action` | workflow | model | renderer |
| `breach` | design | model | renderer |
| `codify` | workflow | model | discipline |
| `conops` | workflow | model | renderer |
| `cover` | design | user | renderer |
| `engineering-doc-writing` | writing | model | discipline |
| `execute` | workflow | model | orchestrator |
| `go-nogo` | meta | model | discipline |
| `herdr` | automation | model | adapter |
| `herdr-carla-tune` | automation | user | orchestrator |
| `neutralize` | debugging | model | discipline |
| `passdown` | workflow | user | adapter |
| `repair` | workflow | user | orchestrator |
| `sanitize` | workflow | user | orchestrator |
| `software-study` | learning | user | orchestrator |
| `tadsim-dynamics-bench` | automation | user | orchestrator |
| `tasking` | workflow | user | orchestrator |
| `traceback` | review | model | discipline |
| `x-likes-digest` | automation | user | adapter |

新增、移除或禁用 skill 时，先更新 `manifest.yaml`，再同步本表，并运行完整验证。

## 目录结构

```text
skills/<skill-name>/
├── SKILL.md            # skill 定义与触发边界
├── references/         # 参考契约（可选）
├── scripts/            # gate 或辅助脚本（可选）
├── evals/              # 触发评测（可选）
└── templates/          # 输出模板（可选）
scripts/
├── install.mjs         # 安装、更新、列出与 doctor
├── skill_telemetry.py  # 隐私安全的本地结果事件
└── ...
manifest.yaml           # skill 注册表
tests/                  # 仓库级契约与安装测试
```

## 贡献与安全

提交 skill 或工作流修改前，请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。安全问题请按 [SECURITY.md](SECURITY.md) 私下报告，不要先开公开 issue。

## 成熟度边界

该仓库仍在快速迭代，尚未发布稳定 release；skill 名称、调用契约和安装范围可能变化。当前没有可核验的外部采用量或兼容性承诺。

## License

[MIT](LICENSE)
