# opensynth

RTL → GDSII in one afternoon, entirely open source.

opensynth is a chip design flow built to be driven by a coding agent: you write a
natural-language `spec.md`, your agent writes tested Verilog, and the deterministic
scripts in this repo take it through synthesis, place-and-route, and signoff on the
open sky130 PDK. No licenses, no GUIs — just [Verilator](https://github.com/verilator/verilator),
[iverilog](https://github.com/steveicarus/iverilog), and
[OpenROAD-flow-scripts](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts),
all running in Docker.

```
spec.md → [rtl-from-spec] → rtl/ → [verify-rtl] → passing tests
        → [synth-pnr] → GDSII → [signoff-gds] → signoff statement
```

Bracketed items are skills in `skills/`. The agent reads the skill for the stage it's
about to run, then executes it via the matching script.

## Repository layout

| Path | What it is |
|---|---|
| `AGENTS.md` | The contract the agent follows: pipeline, rules, stage → skill → script mapping |
| `docs/agent-workflow.md` | How an agent behaves session-to-session: exit codes, `--json`, iteration discipline |
| `docs/walkthrough.md` | Annotated end-to-end run of the counter example with real outputs |
| `skills/` | Five playbooks: `rtl-from-spec`, `verify-rtl`, `synth-pnr`, `signoff-gds`, `debug-env` |
| `scripts/` | Stdlib-only Python wrappers around the EDA tools |
| `templates/` | `spec.template.md` and `design.yaml` for new designs |
| `examples/counter/` | A complete worked example: spec → rtl → tb → GDS |
| `tests/` | Selfcheck suite for the scripts themselves (`tests/test_scripts.py`) |
| `.github/workflows/` | CI: compile-check + selfcheck on every push |

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) running (all EDA tools run in containers)
- Python 3.10+
- Docker images, pulled automatically on first use (~2–5 GB total):
  `hdlc/verilator:latest`, `hdlc/iverilog:latest`, `openroad/orfs:latest`

## Quickstart

Point your agent at the repo — `AGENTS.md` routes it — or run the stages yourself:

```powershell
git clone <this-repo>; cd opensynth

# Run the worked example end-to-end:
python scripts/lint.py  examples/counter    # Verilator lint (-Wall, zero warnings)
python scripts/sim.py   examples/counter    # iverilog self-checking testbench
python scripts/synth.py examples/counter    # OpenROAD-flow-scripts → GDS (10-45 min)
python scripts/report.py examples/counter --check   # signoff gates: slack >= 0, DRC clean

# Output: examples/counter/build/results/sky130hd/counter/base/6_final.gds
```

The first synth run pulls the ORFS image and caches the sky130 PDK; subsequent runs
are much faster. Never edit anything under a design's `build/` — it is generated.

## Starting a new design

1. Create a design directory with `spec.md` (from `templates/spec.template.md`) and
   `design.yaml` (from `templates/design.yaml`). Everything lives under one directory.
2. Tell your agent: *"Implement `mydesign/spec.md` through GDSII following AGENTS.md."*
   It reads `skills/rtl-from-spec`, writes `rtl/`, verifies via `skills/verify-rtl`,
   runs the physical flow via `skills/synth-pnr`, and signs off via `skills/signoff-gds`.
3. Or do it yourself, stage by stage, with the same scripts the agent would run.

## Design directories

Each design is self-contained:

```
mydesign/
  spec.md                     # natural-language spec (from templates/)
  design.yaml                 # tool configuration: name, clocks, area targets
  constraints.user.sdc        # optional: extra SDC (second clocks, false paths, I/O)
  rtl/                        # hand-written RTL
  tb/                         # self-checking testbenches
  build/                      # generated (gitignored): results/, reports/, logs/
```

## Scripts

| Script | Purpose | Exit codes |
|---|---|---|
| `lint.py` | Verilator `--lint-only -Wall` (any warning is a failure) | 0 clean / 1 violations / 2 setup |
| `sim.py` | iverilog self-checking testbenches (any `FAIL` line fails the run) | 0 PASS / 1 FAIL / 2 setup |
| `synth.py` | ORFS RTL→GDS; `--stage synth/floorplan/place/cts/route/final` for partial runs | 0 done / 1 flow fail / 2 setup |
| `report.py` | Timing/area/DRC summary; `--check` enforces the signoff gates | 0 report / 1 gate fail / 2 no results |

All scripts accept `--json` for machine parsing — agents should use it.
Exit codes are contractual: 0 success, 1 flow failure the agent must diagnose,
2 setup/environment error (no point retrying the design).

**Testbench convention:** a testbench must print a line starting with `PASS`
(only if every check passed), must never print a line starting with `FAIL`,
and must reach `$finish` within the 300 s sim timeout. See `skills/verify-rtl/SKILL.md`.

### Testing the flow itself

```powershell
python tests/test_scripts.py # unit checks + docker-backed smoke tests; skips gracefully without docker
```

## Non-negotiables (enforced in AGENTS.md)

- Scripts are the only path to the tools; never run Verilator/iverilog/ORFS make directly.
- A testbench is never modified to make failing RTL pass.
- A spec-set `clock_period_ns` is never loosened to hide a structural timing violation.
- Signoff always states what is *not* proven.

## Signoff honesty

`report.py --check` gates what is machine-provable (post-route timing, routing DRC,
a valid GDS), but some signoff items remain manual. What is proven vs. not — including
no formal equivalence (the ORFS image's LEC tool needs AVX-512, so it is disabled) and
no magic/netgen full DRC/LVS — is spelled out in `skills/signoff-gds/SKILL.md`.
A design is never "done" without those gaps stated explicitly.
