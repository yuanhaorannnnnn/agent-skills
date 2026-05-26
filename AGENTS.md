# Global Agent Guidance
## Purpose
This file defines durable baseline preferences for coding agents working with this user across repositories, including Pi, Claude Code, and Codex.
Use `AGENTS.md` as the canonical shared guidance file. For Claude Code, keep `CLAUDE.md` thin and import this file with `@AGENTS.md` instead of duplicating content.
Keep this file short, behavior-oriented, and repository-agnostic. Do not store project-specific setup, commands, architecture, or temporary task state here. Put those in the target project, nested `AGENTS.md`, skills, scripts, README files, or planning state.
## Scope
Treat these rules as defaults. Project-level guidance may refine or override them with more specific context.
Put specialized or path-specific rules close to the files they govern.
## Communication
Respond in Simplified Chinese unless the user explicitly asks for another language.
Keep technical terms, identifiers, commands, file paths, and code snippets in English.
When the user writes in English, correct only serious issues that make the meaning ambiguous, invert the intended meaning, misuse a critical technical term, or make the sentence unreadable. Ignore minor issues when the meaning is clear.
If correction is needed, append exactly one final line:
`> 💡 "your version" → "suggested version"`
## Skills, Scripts, And Automation
Put reusable agent behavior in skills.
Put executable mechanics in scripts.
Keep instructions runtime-neutral unless a runtime-specific constraint is essential.
Do not duplicate detailed workflows already owned by skills, scripts, README files, or planning documents.
Do not hard-code tool-specific implementation details in global guidance unless they are stable cross-agent constraints.
## Documentation And Visuals
Prefer portable Markdown for repo documentation.
Use richer HTML or visual artifacts only when the requested deliverable benefits from them.
For single-page HTML artifacts, use this local reference catalog when available:
`/media/yhr/2T/files/wiki/raw/assets/thariqs.github.io/html-effectiveness/catalog.md`
If the catalog is not accessible, apply layout judgment based on the requested deliverable type.
Use ASCII diagrams for inline Markdown diagrams when useful. Keep text inside ASCII diagrams in English so alignment stays stable.
When a project has `DESIGN.md`, treat its design tokens as binding constraints for visual work.
Do not leave generated diagrams with disconnected or dangling logic branches.
## Validation
For skill changes, check that edited instructions remain discoverable, scoped, and executable by an agent without hidden context.
For script or package changes, verify the affected behavior before finishing.
If validation is not run, say so clearly in the final response.
## Privacy
Read local agent session data only when the user asks for handoff, restore, debugging, or another task that clearly requires it.
Prefer narrow local paths or identifiers over broad scans of private agent directories.
