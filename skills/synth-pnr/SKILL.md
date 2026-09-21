---
name: synth-pnr
description: Run synthesis and place-and-route through OpenROAD-flow-scripts (sky130) via scripts/synth.py; interpret and fix timing, area, and flow failures. Use after lint+sim pass, or when synth fails.
---

# Synthesis and Place-and-Route

Everything physical happens through `scripts/synth.py`, which drives OpenROAD-flow-scripts (ORFS) in docker. Never invoke ORFS make directly; the script generates the config from `design.yaml`.

## Running

```
python scripts/synth.py <design_dir>                # full flow → GDS (10-45 min typical)
python scripts/synth.py <design_dir> --stage synth  # synthesis only (fast, ~1 min)
```

Stages: `synth` → `floorplan` → `place` → `cts` → `route` → `final`. Intermediate stages are for debugging only — a design isn't done until the full run completes.

Outputs land in `<design_dir>/build/`:
- `results/<platform>/<name>/base/6_final.gds` — the deliverable
- `reports/<platform>/<name>/base/` — timing/DRC reports
- `logs/<platform>/<name>/base/` — per-stage logs (the debugging input)

## What design.yaml controls

| design.yaml | ORFS variable | Notes |
|---|---|---|
| `design.name` | `DESIGN_NAME` | must equal top module |
| `design.platform` | `PLATFORM` | sky130hd default |
| `timing.clock_period_ns` | `clk_period` in SDC | target clock; don't set below ~2ns for sky130hd without reason |
| `area.core_utilization` | `CORE_UTILIZATION` | 35-55 sensible; higher = denser/harder routing |
| `area.place_density` | `PLACE_DENSITY` | sky130hd default 0.60 |

## Interpreting failures (read the log tail synth.py prints)

- **`PDN-0185 Insufficient width ... straps`** — die too small for default met4/met5 PDN straps. opensynth already substitutes a met1/met2 small-die PDN (`scripts/pdn_small.tcl`); if you still see this, the core is tiny — raise `core_utilization` or accept it via the small-die PDN.
- **`Error: cts.tcl ... child killed: illegal instruction`** — known ORFS-image issue with `repair_timing` under CTS on some hosts; `synth.py` exports `SKIP_CTS_REPAIR_TIMING=1` already. If you see it from a manual invocation, set that variable.
- **`LEC_CHECK`/`Kepler Formal` errors** — the ORFS image's formal tool needs AVX-512; `synth.py` disables it (`LEC_CHECK=0 SEC_CHECK=0`). Note this in signoff: equivalence is lint+sim based, not formal, until this is fixed.
- **Timing violations in reports** (negative `worst slack`) — first check whether the clock period is contractual in `spec.md`/`design.yaml`. If the target interval is aspirational (an estimate, not a requirement), relaxing `clock_period_ns` to something achievable is a legitimate first fix. If the period is contractual, see "fixing timing" below — changing the constraint is not a fix.
- **`unconnected port` / `multiple drivers` in synth** — back to RTL bugs; run lint first, it usually catches these.

## Fixing timing violations properly

1. Check `reports/.../6_finish.rpt`: `wns`, `tns`, `worst slack`.
2. If slack is barely negative (> -0.2ns), try `place_density` up a bit or re-run — placement is stochastic.
3. If persistently negative: the RTL has a long combinational path between registers. Fix in RTL (pipeline, retime), not in constraints. A spec-legal `clock_period_ns` is never loosened to make a bad design pass.

## Done means

1. Full flow exits 0 and `6_final.gds` exists.
2. `python scripts/report.py <design_dir>` shows: worst slack ≥ 0, routing DRC clean.
3. If timing was fixed by changing RTL, re-run lint+sim before declaring done.
