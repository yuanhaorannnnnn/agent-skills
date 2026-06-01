---
name: Calibrate
description: |
  General-purpose automatic performance optimization loop. Scans codebase for
  algorithmic complexity and performance hotspots, uses user-provided benchmarks
  to establish baselines, and iteratively optimizes with before/after verification.
  Framework and language agnostic — works with any project.

  Trigger on: "auto optimize", "自动优化", "optimize performance", "性能优化",
  "perf loop", "跑一轮性能优化", "scan for bottlenecks and fix them",
  "优化这个项目的性能", "find performance issues and apply fixes".

  NOT the same as autoresearch-loop — that skill is CARLA LiDAR-specific with a
  fixed compile→benchmark toolchain. Use auto-optimize for any other project.
---

# Auto Optimize

Deeply integrated with `complexity-optimizer` (upstream, read-only analysis skill).
This skill extends its scan→report→risk-assess pipeline into a closed optimization
loop: baseline benchmark → scan hotspots → rank → optimize → verify → repeat.

## Core Rule

Understand current behavior before changing it. Prefer one small, proven
improvement with before/after numbers over a broad rewrite. Report-only by
default — do not edit files until the user asks you to implement.

## Non-Negotiable Constraints

- **Benchmark must exist.** The user provides a measurable benchmark command. If they don't have one, pause and help them create a minimal one before proceeding.
- **Tests pass before starting.** If tests exist, run them. If none exist, flag the risk and ask whether to proceed.
- **One hotspot at a time.** Never batch unrelated optimizations.
- **Benchmark before and after every change.** Only accept a change when the benchmark improves or stays flat (with a valid reason).
- **Discard on regression.** Revert immediately if benchmark degrades or tests break.
- **Preserve behavior.** Output ordering, API contracts, error handling, and edge cases must stay identical unless the user explicitly approves a relaxation.

## Workflow

### Phase 1: Understand the project

Establish:
- Language, framework, build system, test command.
- Performance-sensitive paths (ask the user or infer from structure).
- The benchmark command the user will use.

### Phase 2: Establish baseline

Run the user's benchmark command. Record:
- The exact command and working directory.
- Raw output.
- The key metric value(s) to track.

If the project has no benchmark, help the user write one:
- CLI/script projects: `time <command>` repeated 3-5 times, take median.
- Web/API projects: `curl` timing, `wrk`, `ab`, or equivalent.
- Library code: a minimal Python/JS/Go micro-benchmark script.

### Phase 3: Scan hotspots

First pass — use the complexity-optimizer scanner:

```bash
python3 <agent-platform>/upstream/codex-complexity-optimizer/complexity-optimizer/scripts/analyze_complexity.py <repo> --format markdown
```

The scanner flags O(n^2) loops, nested iteration, repeated scans, N+1 patterns
across Python, JS/TS, Java, Go, C/C++, C#, Ruby, PHP, and Swift. Treat scanner
output as leads, not proof — inspect each flagged site to confirm data sizes
make the complexity matter.

Supplement with manual inspection of:
- Hot paths identified in Phase 1.
- Rendering/recomputation in UI code.
- Database/API query patterns.
- Shared utilities called from many callers.

If the scanner is unavailable (upstream disabled), skip to manual inspection.

### Phase 4: Rank and report

Produce a ranked report using the complexity-optimizer report structure.
Read `references/report-template.md` in the complexity-optimizer upstream for
the canonical format. At minimum, for each finding:

| # | File:Line | Pattern | Current O | Proposed O | Est. Impact | Risk |
|---|-----------|---------|-----------|-------------|-------------|------|

Sort by estimated impact × inverse risk. Include:
- Why the current pattern is costly at expected data sizes.
- The specific change proposed.
- Which tests cover the affected code.
- What benchmark measurement confirms the improvement.

If the user only asked for analysis, stop here. Present the report and ask which
hotspots to implement.

### Phase 5: Optimize (one hotspot at a time)

For each hotspot the user wants to implement:

1. **Run relevant tests** — confirm they pass before any change.
2. **Apply the optimization** — the smallest change that achieves the complexity improvement.
3. **Run tests again** — all must still pass.
4. **Run benchmark** — compare against baseline.
5. **Decide**: keep if improved (or neutral with cleaner code), discard and revert if regressed.

When choosing the optimization strategy, consult the complexity-optimizer
optimization playbook: `references/optimization-playbook.md`. It catalogs common
transformations (nested lookup → map/set, pairwise → sort+two-pointer, N+1 →
bulk fetch, recomputation → memoization) with correctness checks for each.

### Phase 6: Final report

After all optimizations are applied or discarded:

- Per-hotspot: original → new complexity, benchmark delta (%), tests run.
- Aggregate improvement summary.
- Residual risk and follow-up recommendations.
- Use the complexity-optimizer report template structure: Summary, Findings,
  Changes Made, Verification.

## Difference from autoresearch-loop

| | auto-optimize | autoresearch-loop |
|---|---|---|
| Scope | Any project, any language | CARLA LiDAR sensor (C++) |
| Metric | User-provided benchmark | scan_latency_ms_median (fixed) |
| Mechanical layer | None (AI-driven) | loop.py state machine |
| Toolchain | Project's own build/test | Fixed CARLA UE5 compile pipeline |
| Complexity analysis | complexity-optimizer scanner | Manual code inspection |

## Reference files

When you need specific patterns or the canonical report format, read these from
the complexity-optimizer upstream:

- **Scanner**: `upstream/codex-complexity-optimizer/complexity-optimizer/scripts/analyze_complexity.py` — first-pass hotspot detector.
- **Report template**: `upstream/codex-complexity-optimizer/complexity-optimizer/references/report-template.md` — canonical output structure for Phase 4 and Phase 6 reports.
- **Optimization playbook**: `upstream/codex-complexity-optimizer/complexity-optimizer/references/optimization-playbook.md` — common O(n^2)→O(n log n)/O(n) transformations with correctness checks.
