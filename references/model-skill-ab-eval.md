# Model vs Skill A/B Eval

Use `scripts/run_skill_ab_eval.py` to test whether a self-owned skill still adds value beyond the current base model.

## Contract

- Run both arms with the same model, prompt, sandbox, working directory shape, and temporary runtime state.
- Baseline: no self-owned skills mounted.
- Treatment: mount only the target skill and explicitly invoke it.
- Store prompt, expected behavior, responses, return codes, model, and isolation method. Never store credentials, session files, hidden reasoning, or unrelated runtime configuration.
- Judge behavior against the eval oracle. If the oracle assumes unavailable tools or an obsolete architecture, update it transparently and record why; never rewrite captured responses.
- A skill earns retention when it repeatedly improves a stable workflow boundary, gate, artifact, or decision. Mere verbosity or terminology does not count.

## Run

```bash
python3 scripts/run_skill_ab_eval.py \
  --skill-dir skills/codify \
  --evals skills/codify/evals/evals.json \
  --output .eval/skill-durability/codify.json
```

Use `--case-id <id>` for a focused regression after a skill change. Treat live-model output as sampled evidence, not a deterministic unit test.
