# Agents Skills Repo

An agent-neutral GitHub repository for maintaining local skills and exposing them
through `~/.agents/skills`.

## Goal

This repository keeps published skills in Git, without binding the runtime to
Claude-specific plugin directories or Codex-specific command systems.

The runtime surface is always:

```text
~/.agents/skills
```

## Layout

```text
agents/
commands/
scripts/
skills/
scripts/
├── install.sh
└── sync.sh
manifest.yaml
```

`skills/` contains the published skill folders.

## Install

Clone this repository somewhere stable, for example:

```bash
git clone <your-github-repo-url> ~/.agents/repos/agents-skills-repo
bash ~/.agents/repos/agents-skills-repo/scripts/install.sh
```

This links every skill folder that contains `SKILL.md` into `~/.agents/skills`.

## Update

```bash
bash ~/.agents/repos/agents-skills-repo/scripts/sync.sh
```

This performs:

1. `git pull --ff-only`
2. re-link skills into `~/.agents/skills`

## Published Skills

Current published local skills are listed in [manifest.yaml](./manifest.yaml).

## Notes

- This repository only manages `~/.agents/skills`.
- It does not write to `~/.claude/agents`, `~/.claude/commands`, or `~/.claude/skills`.
- Skill-relative script paths are preserved by keeping `skills/` and `scripts/`
  as top-level siblings inside this repository.
