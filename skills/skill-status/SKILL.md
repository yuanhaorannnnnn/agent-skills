---
name: skill-status
description: Query the disable/enable status of skills across all sources
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
