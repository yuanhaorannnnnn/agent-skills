---
name: DoctrineReview
description: |
  Review recent work across all agent runtimes and distill repeated
  manual workflows into skills, subagents, or automations. Use when the
  user wants to find patterns in their work history and package them.
  Trigger on: "distill my workflows", "review my workflows", "packaging
  review", "what should I automate", "identify repeated work", "find
  patterns in my work", "优化工作流", "工作流分析", "封装重复工作",
  "萃取工作流", "30-day review", "60-day review". Also trigger when the
  user asks to look back at work history to find automation opportunities.
---

# Distill

Review recent work across all agent runtimes (Codex, Claude Code, Pi) and distill repeated manual workflows into packaged skills, subagents, or automations.

## Dependencies

This skill requires the `agent-session-index` toolchain. Before starting:

1. Locate the tool — check these paths in order:
   - `<current-repo>/bin/agent-session-index` (most common)
   - `/media/yhr/2T/files/cc_projects/infra/codex/bin/agent-session-index` (fallback)
2. The tool reads session JSONL from:
   - `~/.codex/sessions/` (Codex)
   - `~/.claude/projects/` (Claude Code)
   - `~/.pi/agent/sessions/` (Pi)
3. Expected SQLite output: `.agents/session-index.sqlite`

If the tool is not found, tell the user and stop — do not proceed without it.

## Workflow

### Phase 1: Gather Evidence

Run these steps in order. The first three can run in parallel.

**1.1 Refresh session index**

```bash
python <path-to>/bin/agent-session-index --db .agents/session-index.sqlite refresh
```

**1.2 Query session distribution** — aggregate by project, runtime, and topic.

Key SQL queries to run against `.agents/session-index.sqlite`:

```sql
-- By project and runtime (exclude /tmp noise)
SELECT
  CASE
    WHEN cwd LIKE '%CarlaUE5%' OR cwd LIKE '%carla%' THEN 'CARLA/UE5'
    WHEN cwd LIKE '%wiki%' THEN 'wiki'
    WHEN cwd LIKE '%infra/codex%' THEN 'infra/codex'
    WHEN cwd LIKE '%leap%' THEN 'leap'
    WHEN cwd LIKE '%creer%' THEN 'creer'
    WHEN cwd LIKE '%caffe-map%' THEN 'caffe-map'
    WHEN cwd LIKE '%skyscout%' THEN 'skyscout'
    WHEN cwd LIKE '%test%' THEN 'test/agent-platform'
    WHEN cwd LIKE '%guardstrike%' THEN 'guardstrike'
    WHEN cwd LIKE '%agent-workspaces%' THEN 'agent-workspaces'
    WHEN cwd LIKE '%autoresearch%' THEN 'autoresearch'
    WHEN cwd LIKE '/tmp%' THEN '/tmp (NOISE)'
    ELSE 'other'
  END as project,
  runtime, COUNT(*) as cnt,
  ROUND(AVG(user_turns + assistant_turns), 1) as avg_turns,
  SUM(CASE WHEN has_errors THEN 1 ELSE 0 END) as errors,
  SUM(CASE WHEN has_verification THEN 1 ELSE 0 END) as verified
FROM sessions
WHERE started_at > datetime('now', '-60 days')
GROUP BY project, runtime ORDER BY cnt DESC;
```

```sql
-- Repeated first user messages (same task re-initiated)
SELECT first_user_message, COUNT(*) as cnt
FROM sessions
WHERE started_at > datetime('now', '-60 days')
  AND cwd NOT LIKE '/tmp%'
  AND first_user_message IS NOT NULL AND first_user_message != ''
GROUP BY first_user_message HAVING cnt >= 2
ORDER BY cnt DESC LIMIT 30;
```

```sql
-- Topic categorization from last_user_message
SELECT
  CASE
    WHEN last_user_message LIKE '%sensor%' OR last_user_message LIKE '%相机%'
      OR last_user_message LIKE '%lidar%' OR last_user_message LIKE '%tof%'
      OR last_user_message LIKE '%rgbd%' OR last_user_message LIKE '%thermal%'
      THEN 'sensor/camera/lidar'
    WHEN last_user_message LIKE '%skill%' OR last_user_message LIKE '%agent%'
      OR last_user_message LIKE '%mcp%' THEN 'skill/agent/mcp'
    WHEN last_user_message LIKE '%restore%' OR last_user_message LIKE '%save%'
      OR last_user_message LIKE '%handoff%' THEN 'session management'
    WHEN last_user_message LIKE '%build%' OR last_user_message LIKE '%compile%'
      OR last_user_message LIKE '%cmake%' THEN 'build/compile'
    WHEN last_user_message LIKE '%review%' OR last_user_message LIKE '%审查%'
      THEN 'code review'
    WHEN last_user_message LIKE '%deploy%' OR last_user_message LIKE '%cloudflare%'
      THEN 'deployment'
    ELSE 'other'
  END as category, COUNT(*) as cnt
FROM sessions
WHERE started_at > datetime('now', '-60 days')
  AND cwd NOT LIKE '/tmp%'
GROUP BY category ORDER BY cnt DESC;
```

**1.3 Read memories and rollout summaries**

Read these files for patterns:
- `~/.codex/memories/MEMORY.md` — task groups, user preferences, failure lessons
- `~/.codex/memories/rollout_summaries/*.md` — per-session keywords and decisions

Extract: task groups, user preferences, failures/learnings, repeated keywords across rollouts.

**1.4 Scan existing skills coverage**

Scan all skill directories for installed skills:
- `/home/yhr/.claude/skills/`
- `/home/yhr/.claude/plugins/`
- `/home/yhr/.agents/repos/agent-skills/skills/`
- `/home/yhr/.agents/skills/`
- `/home/yhr/.codex/skills/`
- `<current-repo>/skills/`

Also check for custom subagents at `~/.claude/agents/` and `~/.codex/agents/`, and existing automations at `~/.claude/scheduled_tasks.json` and `~/.codex/scheduled_tasks.json`.

### Phase 2: Analyze and Shortlist

Cross-reference the evidence from Phase 1:

1. **Group sessions by project** — which repos dominate?
2. **Identify repeated user messages** — same task re-initiated across sessions = strong signal
3. **Extract topic clusters** — sensor work, skill ops, session management, build issues, etc.
4. **Cross-reference with existing skills** — for each cluster, check if a skill already covers it
5. **Check memory for patterns** — task groups, user preferences, failures

### Phase 3: Apply Decision Filters

For each candidate, apply these filters:

| Filter | Check |
|--------|-------|
| Recurrence | Occurred at least twice, or clearly will recur |
| Stable I/O | Has stable inputs, repeatable procedure, clear stopping condition |
| Impact | Would materially improve speed, quality, consistency, or reliability |
| Gap | Not already adequately covered by existing skill/subagent/automation |

Only proceed with candidates that pass ALL four filters.

### Phase 4: Choose Form

Pick the smallest appropriate form:

- **Skill** — a reusable workflow or playbook. Use when the workflow involves decision-making, multi-step context-gathering, or domain-specific judgment
- **Custom subagent** — a bounded specialist role. Use for delegation of well-scoped investigation or implementation tasks
- **Automation** — a scheduled check, report, or monitor. Use for periodic, non-interactive tasks (cron, pre-commit hook, health check)
- **Extend existing** — add to an existing skill or tool. Use when 80% of the need is already met
- **Skip** — mark clearly why: too one-off, ambiguous, sensitive, poorly evidenced, or already covered

### Phase 5: Create and Report

1. Create only the high-confidence missing items. Keep them narrow, practical, and source-aware
2. Validate any created skill with `skill-creator`'s validation script if available
3. Produce the final report

## Output Format

Always structure the final report like this:

```
## N-Day Workflow Packaging Review

### Data Scope
- Time window, total sessions, runtime breakdown
- Projects covered, skills installed, automations existing

### Shortlist

| # | Candidate | Evidence | Freq/Conf | Form | Decision |
|---|-----------|----------|-----------|------|----------|
| 1 | ... | ... | ... | Skill/Automation/... | Created/Skip/Needs evidence |

### Decisions
- **Created**: what was created, where, what it covers
- **Skipped**: what was skipped and why (one sentence each)
- **Needs evidence**: what might be worth packaging if more evidence accumulates
```

## Remember

- `/tmp` sessions are noise (AGENTS.md injections) — always exclude them
- `pi-mono` sessions are mostly runtime config tests — weight them lower
- Session management commands (`$restore-conversation`, `$save-conversation`) appearing as user messages don't indicate a gap — they're usage of already-existing skills
- The goal is finding **uncovered** gaps, not validating what's already automated
- Prefer skipping over creating — a false positive skill is worse than a missed opportunity
- If an existing skill covers 80% of a need, recommend extending it rather than creating a new one
- When creating, default to narrow scope; broad skills rot faster
