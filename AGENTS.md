# opensynth — Agent Guide

AI-assisted RTL → GDSII flow. You (the coding agent) are the orchestrator; this repo provides the knowledge (skills/) and the deterministic tools (scripts/). All EDA tools run in docker.

## The pipeline

```
spec.md → [rtl-from-spec] → rtl/ → [verify-rtl] → passing tests
        → [synth-pnr] → GDSII → [signoff-gds] → signoff statement
```

Bracketed items are skills in `skills/`. Read the relevant skill before starting a stage.

## Prerequisites (check once per session)

1. Docker daemon running: `docker info` must succeed. All tools (verilator, iverilog, OpenROAD/ORFS) run inside containers; nothing else needs installing.
2. Images (pull on first use, ~2-5GB total): `hdlc/verilator:latest`, `hdlc/iverilog:latest`, `openroad/orfs:latest`.

## Stage → skill → script mapping

| Stage | Read | Run | Done when |
|---|---|---|---|
| 1. Understand the design | `skills/rtl-from-spec` | — | spec + design.yaml read, ambiguities resolved |
| 2. Write RTL | `skills/rtl-from-spec` | `python scripts/lint.py <dir>` | lint exits 0, 0 warnings |
| 3. Write tests + verify | `skills/verify-rtl` | `python scripts/sim.py <dir>` | sim exits 0 (PASS) |
| 4. Synthesis + P&R | `skills/synth-pnr` | `python scripts/synth.py <dir>` | `6_final.gds` exists |
| 5. Signoff | `skills/signoff-gds` | `python scripts/report.py <dir>` | report: slack ≥ 0, DRC clean, honest gaps stated |

`<dir>` is the design directory (e.g. `examples/counter`), which must contain `design.yaml`.

## Non-negotiable rules

- **Scripts are the only path to the tools.** Never run verilator/iverilog/ORFS make directly.
- **Never modify a testbench to make failing RTL pass** (see verify-rtl for the spec-change exception).
- **Never loosen `clock_period_ns` to hide a timing violation** caused by RTL structure.
- **Always state signoff gaps** when declaring a design done (see signoff-gds).
- Scripts exit 0 on success, 1 on failure, 2 on setup errors; all accept `--json` for machine parsing.
- Iterate with small diffs: one hypothesis per sim/synth run, read the failure, fix, re-run.

## Reference design

`examples/counter/` is a complete worked example: `spec.md` → `rtl/counter.v` → `tb/counter_tb.v` → `build/results/sky130hd/counter/base/6_final.gds`. When in doubt about any convention, copy what counter does.

## Starting a new design

1. Create `<design_dir>/` with `spec.md` (use `templates/spec.template.md`) and `design.yaml` (use `templates/design.yaml`).
2. Follow stages 1-5 above.
