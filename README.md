# agent-skills

An agent-neutral skills distribution repository. It maintains published skills in Git and exposes them through `~/.agents/skills` — without binding to Claude-specific plugin directories, Codex-specific command systems, or any particular agent runtime.

## What this repository is

- A **pure skill publishing repository**.
- Each skill is a self-contained folder under `skills/`.
- Shared runtime scripts live under `scripts/` and are reachable from skills via relative paths.
- The final runtime surface is always:
  ```text
  ~/.agents/skills
  ```

## How to install

Clone this repository somewhere stable (for example `~/.agents/repos/agent-skills`), then run the installer:

```bash
git clone https://github.com/yuanhaorannnnnn/agent-skills.git ~/.agents/repos/agent-skills
bash ~/.agents/repos/agent-skills/scripts/install.sh
```

Or, if you prefer Node / npx:

```bash
git clone https://github.com/yuanhaorannnnnn/agent-skills.git ~/.agents/repos/agent-skills
cd ~/.agents/repos/agent-skills
npx agent-skills install
```

The installer will:
- discover every skill that contains `SKILL.md`
- link only `enabled` skills into `~/.agents/skills`
- clean up stale links previously created by this repository

## How to update

```bash
bash ~/.agents/repos/agent-skills/scripts/update.sh
```

Or with npx:

```bash
cd ~/.agents/repos/agent-skills
npx agent-skills update
```

This performs `git pull --ff-only` followed by a re-install.

## Published skills

| Skill | Category | Description |
|---|---|---|
| `capture-mistake-rule` | workflow | Record mistakes and lessons learned as durable rules. |
| `code-reviewer` | review | Review diffs and recent changes for correctness and maintainability. |
| `fix-issue` | debugging | Fix bugs, regressions, and runtime errors with root-cause focus. |
| `repo-agent-bootstrap` | repo | Initialize or normalize a repository into the standard repo-local agent layout. |
| `restore-conversation` | conversation | Resume work from saved conversation context. |
| `save-conversation` | conversation | Persist conversation context for future restoration. |
| `skill-cheatsheet` | utility | Generate a searchable HTML cheatsheet of installed skills. |
| `task-report-slides` | reporting | Create a task-focused HTML presentation deck after work is finished. |

## CLI commands

When installed via npx:

```bash
npx agent-skills install   # Link skills to ~/.agents/skills
npx agent-skills update    # git pull --ff-only + install
npx agent-skills list      # List enabled skills by category
npx agent-skills doctor    # Check links, SKILL.md, and shared scripts
```

## Notes

- This repository only manages `~/.agents/skills`.
- It does not write to `.claude/`, `.codex/`, or any agent-specific directories.
- Skill-relative script paths are preserved by keeping `skills/` and `scripts/` as top-level siblings inside this repository.
