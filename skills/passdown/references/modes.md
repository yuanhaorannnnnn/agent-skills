# Passdown modes

## Modes

`--former` is optional. When omitted, auto-detects sessions from all four runtimes (Codex + Pi + Claude Code + DSH) and merges by recency.

`--dir` defaults to current working directory when not specified.

### Same-directory handoff（最简）

```bash
python3 <skill-dir>/scripts/extract_handoff.py --focus "<topic>" --json
```

Auto-detect runtime, default to current cwd.

### Fresh-conversation rollover handoff

Start a fresh conversation in the same workspace, then invoke passdown with the
source runtime and focus. Passdown performs the handoff; same-runtime rollover
may archive the source under the contract below.

```text
/passdown --former codex --focus "<current topic>"
```

```bash
python3 <skill-dir>/scripts/extract_handoff.py \
  --former codex --focus "<current topic>" --json
```

The default 8000-token budget requires no new argument. Use
`--max-tokens 4000` for a more aggressive handoff.

### Same-runtime rollover archival

Archiving the source conversation is an optional lifecycle action, not part of
extraction. Never archive merely because the extractor ran.

Archive only when all of these hold:

- source and successor use the same runtime (Codex→Codex, Claude→Claude, Pi→Pi, DSH→DSH);
- the user asked for rollover cleanup, or a standing rollover policy authorizes it;
- the successor exists and its first handoff response is valid: completed, non-empty, and not `systemError` or `needs-attention`;
- the source is idle and is neither the current conversation nor a registered Herdr agent;
- the runtime exposes a conversation-archive operation.

If any condition is unknown or fails, leave the source untouched and report the
source session id plus the blocker. If the conditions hold but authorization is
missing, ask first; never archive silently. Archival must be reversible: if the
successor later fails, restore the source conversation.

Codex: archive through the runtime thread lifecycle (`Thread/archive` via
app-server RPC, or `set_thread_archived` in MCP tooling). The handoff automation
around `session_handoff_scan.py` owns scan/dedup state. Never edit, move, or
delete session JSONL.

### Cross-directory handoff

```bash
python3 <skill-dir>/scripts/extract_handoff.py --dir /absolute/source/workspace --focus "<topic>" --json
```

Auto-detect runtime in given directory.

### Specific runtime(s)

```bash
python3 <skill-dir>/scripts/extract_handoff.py --former claude --dir /absolute/workspace --focus "<topic>" --json
```

### Multi-runtime / multi-directory

```bash
# Scan both Claude Code and Codex sessions across two workspaces
python3 <skill-dir>/scripts/extract_handoff.py --former claude,codex --dir /project/a --dir /project/b --json

# Scan all runtimes across multiple directories
python3 <skill-dir>/scripts/extract_handoff.py --dir /project/a,/project/b,/project/c --json
```


### Cross-model handoff: Review + Passdown (DeepSeek/Gemini → GPT)

Triggered when the successor/target is a GPT model (Codex Terra/Sol/Luna, ChatGPT) and the former/source is DeepSeek or Gemini (DSH, `deepseek-v4-flash`, Gemini CLI, Antigravity proxy).

Never ingest unvetted DeepSeek/Gemini turns directly into the GPT successor context as ground truth. Run a read-only evidence review on the extracted turns, decisions, and artifacts *before* completing the handoff:

1. **Evidence & causality audit**: Separate verified runtime facts (test outputs, logs, media) from static code observations and unverified model conjectures. Reject treating static/steady-state correlation as dynamic root cause.
2. **Metric & artifact sanity**: Verify that referenced file paths, media, and scripts exist on disk; check for silent metric bugs (e.g. invalid boundary fits, missing sensitivity baselines, or unhandled warmup frames).
3. **Disposition & vetted handoff**: Flag or downgrade unverified assertions. Present the Review Gate findings first, then emit the vetted handoff structure so the downstream GPT model acts only on proven conclusions.


### zvec-backed focused retrieval

zvec is integrated as a candidate retriever only. It changes how matching session files are found; it does not change parsing, compression, handoff format, or the original JSONL source of truth.

```bash
# Build/rebuild the local zvec index for the current workspace
python3 <skill-dir>/scripts/zvec_index.py --dir "$PWD" --rebuild

# Query through passdown. auto uses zvec for focused queries when available,
# then falls back to the legacy keyword/mtime retriever.
python3 <skill-dir>/scripts/extract_handoff.py --dir "$PWD" --focus "<topic>" --retriever auto --json

# Force zvec. Fails if the index is missing or has no candidate.
python3 <skill-dir>/scripts/extract_handoff.py --dir "$PWD" --focus "<topic>" --retriever zvec --json
```

Index location defaults to `~/.agents/passdown-zvec-index`. Override with `PASSDOWN_ZVEC_PATH=/path/to/index`.

### Direct session file

```bash
python3 <skill-dir>/scripts/extract_handoff.py --file /absolute/session.jsonl --former claude --json
```

## Parameters

- `--former <codex|pi|claude|dsh,...>` — optional, comma-separated. Auto-detect from all four runtimes if omitted. Multi-runtime matches sorted by mtime desc.
- `--dir <path>` — optional, repeatable. Accepts multiple paths via `--dir /a --dir /b` or `--dir /a,/b`. Defaults to current working directory.
- `--file <path>` — direct session JSONL path; bypass discovery.
- `--session <id>` — select one source session by UUID or filename stem.
- `--focus "<topic>"` — find ALL matching sessions across runtimes. Extracts and deduplicates turns from every session with a non-zero focus score.
- `--max-tokens <n>` — hard cap for returned turns. Defaults to 8000 estimated tokens.
- `--retriever <auto|keyword|zvec>` — candidate retrieval mode. `auto` uses zvec for focused queries when an index exists, then falls back to keyword/mtime; `zvec` is strict; `keyword` preserves legacy behavior.
