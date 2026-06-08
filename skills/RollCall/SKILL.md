---
name: RollCall
description: |
  Query the disable/enable status of skills across all sources.
  Use when the user wants to check which skills or upstreams are enabled,
  disabled, or blocked per-agent. Trigger on: "skill status", "查看技能状态",
  "哪些 skill 被禁用了", "check skill status", "skill enable status",
  "show disabled skills", or when the user is debugging why a certain
  skill isn't triggering.
---

# skill-status

Query the disable/enable status of skills across all sources.

## Usage

### Query disabled upstreams and per-agent settings

```bash
bash /media/yhr/2T/files/cc_projects/test/scripts/show_disabled_status.sh
```

Filter by agent:

```bash
bash /media/yhr/2T/files/cc_projects/test/scripts/show_disabled_status.sh --agent claude
```

Filter by upstream:

```bash
bash /media/yhr/2T/files/cc_projects/test/scripts/show_disabled_status.sh --upstream gstack-repo
```

### List enabled self-owned skills

```bash
node ~/.agents/repos/agent-skills/scripts/install.mjs list
```

### Run doctor check (verify all symlinks)

```bash
node ~/.agents/repos/agent-skills/scripts/install.mjs doctor
```

## What It Shows

- **Global disabled upstreams**: Entire upstream repos disabled for all agents
- **Per-agent disabled**: Skills disabled only for specific agent runtimes
- **Per-agent whitelist**: Skills explicitly enabled despite global disable
- **Self-owned disabled**: Skills with `enabled: false` in `manifest.yaml`
- **Physically disabled**: Skills moved to `upstream/.disabled/`

## Canon 输出边界

读取共享契约：`/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md`。

- Skill enable/disable status is runtime inspection. Write Canon only when a durable enable/disable policy, incident, or migration decision is made.
- Canon update-card path, when needed: `/media/yhr/2T/Canon/raw/update-cards/<date>-rollcall-<topic>.md`.
