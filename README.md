# agent-skills

An agent-neutral skills distribution repository. It maintains published skills in Git and exposes them through the local skill runtime directories used by coding agents.

## What this repository is

- A **pure skill publishing repository**.
- Each skill is a self-contained folder under `skills/`.
- Shared runtime scripts live under `scripts/` and are reachable from skills via relative paths.
- Runtime surfaces:
  ```text
  ~/.agents/skills
  ~/.claude/skills
  ~/.codex/skills
  ~/.kimi/skills
  ~/.pi/agent/skills
  ```

## How to install

Clone this repository somewhere stable (for example `~/.agents/repos/agent-skills`), then run the installer:

```bash
git clone https://github.com/yuanhaorannnnnn/agent-skills.git ~/.agents/repos/agent-skills
bash ~/.agents/repos/agent-skills/scripts/install.sh
```

Or, if you prefer the Node CLI entrypoint:

```bash
git clone https://github.com/yuanhaorannnnnn/agent-skills.git ~/.agents/repos/agent-skills
cd ~/.agents/repos/agent-skills
npm exec -- agent-skills install
```

Or install and run directly from GitHub without keeping a local clone:

```bash
npm exec --yes --package=github:yuanhaorannnnnn/agent-skills -- agent-skills install
```

Once `@yuanhaorannnnnn/agent-skills` is published to npm, the registry form becomes:

```bash
npx @yuanhaorannnnnn/agent-skills install
```

The installer will:
- discover every skill that contains `SKILL.md`
- link only `enabled` skills into the supported runtime skill directories
- clean up stale links previously created by this repository

## How to update

```bash
bash ~/.agents/repos/agent-skills/scripts/update.sh
```

Or with the Node CLI entrypoint:

```bash
cd ~/.agents/repos/agent-skills
npm exec -- agent-skills update
```

Or directly from GitHub:

```bash
npm exec --yes --package=github:yuanhaorannnnnn/agent-skills -- agent-skills update
```

This performs `git pull --ff-only` followed by a re-install.

## Published skills

| Skill | Category | Description |
|---|---|---|
| `capture-mistake-rule` | workflow | Record mistakes and lessons learned as durable rules. |
| `code-reviewer` | review | Review diffs and recent changes for correctness and maintainability. |
| `fix-issue` | debugging | Fix bugs, regressions, and runtime errors with root-cause focus. |
| `plan-workspace` | planning | Create and maintain conversation-scoped planning workspaces with spec, ExecPlan, task index, findings, and progress files. |
| `scaffold` | repo | Initialize or normalize a repository into the standard repo-local agent layout. |
| `restore-conversation` | conversation | Resume work from saved conversation context. |
| `save-conversation` | conversation | Persist conversation context for future restoration. |
| `skill-cheatsheet` | utility | Generate a searchable HTML cheatsheet of installed skills. |
| `report` | reporting | Generate a Markdown technical report in academic paper structure after work is finished. |

## CLI commands

When running through the local package bin:

```bash
npm exec -- agent-skills install   # Link skills to ~/.agents/skills
npm exec -- agent-skills update    # git pull --ff-only + install
npm exec -- agent-skills list      # List enabled skills by category
npm exec -- agent-skills doctor    # Check links, SKILL.md, and shared scripts
```

When running directly from GitHub:

```bash
npm exec --yes --package=github:yuanhaorannnnnn/agent-skills -- agent-skills install
npm exec --yes --package=github:yuanhaorannnnnn/agent-skills -- agent-skills update
npm exec --yes --package=github:yuanhaorannnnnn/agent-skills -- agent-skills list
npm exec --yes --package=github:yuanhaorannnnnn/agent-skills -- agent-skills doctor
```

When running from the published npm package, use:

```bash
npx @yuanhaorannnnnn/agent-skills install
npx @yuanhaorannnnnn/agent-skills update
npx @yuanhaorannnnnn/agent-skills list
npx @yuanhaorannnnnn/agent-skills doctor
```

Equivalent `npm exec` form:

```bash
npm exec --yes --package=@yuanhaorannnnnn/agent-skills -- agent-skills install
npm exec --yes --package=@yuanhaorannnnnn/agent-skills -- agent-skills update
npm exec --yes --package=@yuanhaorannnnnn/agent-skills -- agent-skills list
npm exec --yes --package=@yuanhaorannnnnn/agent-skills -- agent-skills doctor
```

## Notes

- This repository manages local skill links for `~/.agents/skills`, `~/.claude/skills`, `~/.codex/skills`, `~/.kimi/skills`, and `~/.pi/agent/skills`.
- Skill-relative script paths are preserved by keeping `skills/` and `scripts/` as top-level siblings inside this repository.
