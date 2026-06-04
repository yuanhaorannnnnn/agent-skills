# Agent Skills

自建 skill 的创建与迭代。

- `skills/<SkillName>/SKILL.md` — name + description（触发层）+ 指令体
- `manifest.yaml` — 注册 + 启用/禁用
- `scripts/install.mjs` — symlink 到 `~/.agents/skills` / `~/.claude/skills`
