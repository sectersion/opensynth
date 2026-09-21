# opensynth

AI-assisted RTL → GDSII flow: give a coding agent a natural-language spec, get back tested RTL and a DRC-clean GDSII, using only open-source tools (Verilator, iverilog, OpenROAD-flow-scripts) running in Docker.

```
spec.md → RTL → lint → testbench sim → synthesis/P&R (sky130) → GDSII → signoff
```

The coding agent is the orchestrator. This repo gives it:
- **`skills/`** — markdown playbooks (RTL rules, testbench conventions, P&R debugging, signoff criteria)
- **`scripts/`** — deterministic Python wrappers around the EDA tools
- **`examples/counter/`** — a complete worked example from spec to GDS

## Quickstart

Prerequisites: [Docker Desktop](https://www.docker.com/products/docker-desktop/) running, Python 3.10+.

```powershell
# 1. Clone, then point your agent at the repo (AGENTS.md routes it), or run manually:

# 2. Run the worked example end-to-end:
python scripts/lint.py  examples/counter    # Verilator lint
python scripts/sim.py   examples/counter    # iverilog self-checking testbench
python scripts/synth.py examples/counter    # OpenROAD-flow-scripts → GDS (10-45 min)
python scripts/report.py examples/counter   # timing/area/DRC summary

# Output: examples/counter/build/results/sky130hd/counter/base/6_final.gds
```

First synth run pulls ~2-5GB of docker images and caches the sky130 PDK; subsequent runs are much faster.

## Start a new design

1. `mkdir mydesign` with `spec.md` (from `templates/spec.template.md`) and `design.yaml` (from `templates/design.yaml`).
2. Tell your agent: *"Implement `mydesign/spec.md` through GDSII following AGENTS.md."* It reads `skills/rtl-from-spec`, writes `rtl/`, tests via `skills/verify-rtl`, then runs the physical flow via `skills/synth-pnr` and signs off via `skills/signoff-gds`.
3. Or do it yourself stage by stage with the same scripts.

## Design directories

Each design is self-contained: `spec.md`, `design.yaml`, `rtl/`, `tb/`, and a generated `build/` (gitignore it). See `examples/counter/`.

## Scripts

| Script | Purpose | Exit codes |
|---|---|---|
| `lint.py` | Verilator `--lint-only -Wall` (warnings are failures) | 0 clean / 1 violations / 2 setup |
| `sim.py` | iverilog self-checking testbenches (fails on any `FAIL` line) | 0 PASS / 1 FAIL / 2 setup |
| `synth.py` | ORFS RTL→GDS (`--stage` for partial runs) | 0 done / 1 flow fail / 2 setup |
| `report.py` | timing/area/DRC summary (`--check` enforces signoff gates) | 0 report / 1 gate fail / 2 no results |

All scripts accept `--json` for machine parsing.

## Signoff honesty

`report.py` + `skills/signoff-gds` distinguish what's proven (post-route timing, routing DRC, passing tests) from what's not (magic/netgen full DRC/LVS, pad ring, formal equivalence). Always state the gaps — see `skills/signoff-gds/SKILL.md`.
