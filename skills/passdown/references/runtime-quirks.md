# Passdown runtime quirks

## Agent-Specific Quirks

- **Fresh conversation**: use passdown from the new conversation; do not `resume` or `fork` the old transcript when reducing conversation context.
- **Codex guardian-wrapped sessions**: The real conversation is often in `>>> TRANSCRIPT` blocks inside `user_message` / `input_text`, not assistant `output_text`.
- **Codex sessions are per-rollout**: Multiple JSONL files may exist per day. Use cwd first, then focus score, then recency.
- **Pi**: Sessions are keyed by working directory. If multiple sessions exist, focus score ranks them before recency.
- **DSH**: Sessions are zstd-compressed (`session.jsonl.zstd` under `~/.dsh/sessions/<slug>/<session-id>/`) and keyed by working directory + session id. User turns come from `user/message` events with `source.kind == "user"`; plugin/instruction injections are dropped, as are `reasoning` content blocks.
- **Claude Code slug**: Project directory slug replaces both `/` and `_` with `-`.
- **Same-runtime handoff**: Claude→Claude, Codex→Codex, Pi→Pi, DSH→DSH are valid. The source session JSONL may still be live; read only. Archive it only after a verified successor and only through the runtime's conversation lifecycle.
- **DeepSeek/Gemini → GPT handoff (`review+passdown`)**: Non-GPT models have a higher incidence of mistaking static code observations for verified root causes, omitting sensitivity baselines, or advancing unverified hypotheses as facts. When a GPT model takes over a DeepSeek or Gemini session, it must run `review+passdown`: audit the source evidence, check real files/metrics on disk, downgrade unverified claims, and only then proceed.
