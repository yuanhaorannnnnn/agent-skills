# agent-skills

**Portable skills for coding agents. Install once, run in Claude Code and Codex.**

English | [中文](README.zh-CN.md)

[![CI](https://github.com/yuanhaorannnnnn/agent-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/yuanhaorannnnnn/agent-skills/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Node](https://img.shields.io/badge/node-%3E%3D18-brightgreen.svg)](package.json)
[![skills.sh](https://skills.sh/b/yuanhaorannnnnn/agent-skills)](https://skills.sh/yuanhaorannnnnn/agent-skills)

![agent-skills](assets/social-preview.png)

For people building repeatable agent workflows: coding-agent users who want a task to leave evidence, reviewers who need an explicit verification step, and maintainers who do not want a growing folder of unscoped prompts.

Not a prompt dump. Every skill declares its trigger boundary, gates and artifacts. The repository ships contract tests plus a `doctor` that fails when the manifest, skill directories and installed links disagree.

`manifest.yaml` is the source of truth for each skill's `enabled` flag, category, invocation mode, role, `calls` dependencies and `handoffs` ownership transfers, and it maps one-to-one onto `skills/*/SKILL.md`. A handoff starts a separate independent skill execution; it is not a call and cannot create user-to-user nesting. The installer symlinks the enabled set into the generic Agents directory and the Claude Code directory, so the source stays single.

## Install and verify in 30 seconds

```bash
npx skills add yuanhaorannnnnn/agent-skills -s neutralize -a codex
```

This installs one skill through the standard `skills` CLI. Use the clone-based path below when you want to inspect the repository itself or run its local `doctor` check.

## Why this is not another prompt collection

- **Declarative registry** — `manifest.yaml` records `enabled`, `category`, `invocation`, `role`, `calls` and ownership `handoffs` per skill; `doctor` validates both graphs and keeps calls restricted to model-invoked skills while handoffs stay between independent user-invoked orchestrators/adapters.
- **Contract tests** — repository-level tests check skill directories, references, invocation boundaries and workflow state; CI runs `doctor` plus three test suites on every push and pull request.
- **Agent-neutral** — the installer only creates symlinks. It does not bind to one product and does not overwrite links owned by other sources.
- **Gates before actions** — high-risk workflows encode confirmation, verification and external state changes as explicit gates instead of running by default.

## Quick start

**Option 1 — the standard skills CLI** (no clone required)

```bash
npx skills add yuanhaorannnnnn/agent-skills                                   # install all
npx skills add yuanhaorannnnnn/agent-skills --list                            # preview first
npx skills add yuanhaorannnnnn/agent-skills -s neutralize -a codex            # one skill
```

**Option 2 — clone and install locally** (Node.js 18+)

```bash
git clone https://github.com/yuanhaorannnnnn/agent-skills.git ~/.agents/repos/agent-skills
cd ~/.agents/repos/agent-skills
npm ci
node scripts/install.mjs install
node scripts/install.mjs doctor
```

The installer links every enabled skill plus the shared `.scripts` directory:

```text
~/.agents/skills/
~/.claude/skills/
```

Updating later:

```bash
node scripts/install.mjs update    # git pull --ff-only, then reinstall
```

## A concrete workflow

Suppose a coding-agent change fails in CI. Start with `neutralize` to record the reproduction and root-cause evidence, use `traceback` to check the approved plan against the implementation and executed tests, then use `sanitize` to scope the resulting commit and closeout record. Each stage has a declared boundary: `neutralize` diagnoses and fixes the defect; `traceback` does not replace tests; `sanitize` does not publish unrelated work.

Minimal local check after installation:

```bash
node scripts/install.mjs doctor
```

`doctor` exits non-zero when the enabled manifest entries, source skill directories or installed links disagree. That is the smallest reproducible check that the installed skill set is internally consistent.

## The workflow it encodes

```text
INTAKE           STUDY            EXECUTE          VERIFY           SHIP
┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐
│passdown    │   │chart       │   │execute     │   │traceback   │   │sanitize    │
│handoff     │   │study hub   │   │run task    │   │align       │   │close out   │
└────────────┘   └────────────┘   └────────────┘   └────────────┘   └────────────┘

When something breaks: neutralize (root cause) → repair (bug ticket) → traceback (regression alignment)
When something is learned: codify (guardrail) → after-action (post-mortem)
```

Skills also fire from their own trigger boundaries: design docs route to `conops`, incident write-ups to `after-action`.

## Skill catalog

| Skill | Category | Invocation | Role | What it does |
|---|---|---|---|---|
| `acquisition` | media | user | adapter | Ingest videos, articles and PDFs into a knowledge base |
| `after-action` | workflow | model | renderer | Write a post-mortem for a hard fix |
| `breach` | design | model | renderer | Single-page HTML deliverables (status, flowcharts, digests) |
| `chart` | learning | user | orchestrator | Build a durable Study Hub for a repo or product |
| `codify` | workflow | model | discipline | Distill one reusable guardrail from a mistake |
| `conops` | workflow | model | renderer | Technical design document for review |
| `cover` | design | user | renderer | Generate a DESIGN.md token spec |
| `execute` | workflow | model | orchestrator | Run a task and leave a resumable record |
| `go-nogo` | meta | model | discipline | Decide whether a new skill or tool is worth building |
| `herdr` | automation | model | adapter | Inspect and drive Herdr panes |
| `neutralize` | debugging | model | discipline | Root-cause a defect, then scan for the same pattern nearby |
| `paperwork` | writing | model | discipline | Draft or rewrite technical documents around reader task and evidence |
| `passdown` | workflow | user | adapter | Hand off context from another agent session |
| `repair` | workflow | user | orchestrator | Four-stage bug-ticket workflow (Yunxiao) |
| `sanitize` | workflow | user | orchestrator | Close out a task with commits, or write a full technical report |
| `tasking` | workflow | user | orchestrator | Four-stage requirement workflow (Yunxiao) |
| `traceback` | review | model | discipline | Design → implementation → tests alignment gate |
| `x-likes-digest` | automation | user | adapter | Weekly digest of liked posts on X |

Adding, removing or disabling a skill means editing `manifest.yaml` first, then this table, then running the full verification.

## Verification

```bash
node scripts/install.mjs list       # list enabled skills by category
node scripts/install.mjs doctor     # check manifest, skill dirs and installed links

python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m unittest discover -s skills/acquisition/tests -p 'test_*.py'
python3 -m unittest discover -s skills/passdown/tests -p 'test_*.py'
```

CI runs the same commands on every push and pull request; the badge above is the result, not a claim.

## Repository layout

```text
skills/<skill-name>/
├── SKILL.md            # skill definition and trigger boundary
├── references/         # reference contracts (optional)
├── scripts/            # gates and helper scripts (optional)
├── evals/              # trigger evals (optional)
└── templates/          # output templates (optional)
scripts/
├── install.mjs         # install, update, list, doctor
├── skill_telemetry.py  # privacy-safe local outcome events
└── ...
manifest.yaml           # skill registry
tests/                  # repository contract and install tests
```

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md) before changing a skill or workflow. Report security issues privately through [SECURITY.md](SECURITY.md) instead of opening a public issue.

## Maturity boundaries

The repository is iterating quickly and has no stable release; skill names, invocation contracts and install scope can change. There is no externally verified adoption or compatibility promise yet.

**Language:** the skill bodies are currently written in Chinese, because that is the language they were developed and used in. The `description` frontmatter and the catalog above are the reliable English entry point. A translated English pass over the skill bodies is planned, not shipped — treat this README as accurate about what exists today.

## License

[MIT](LICENSE)
