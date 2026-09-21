---
name: signoff-gds
description: Judge whether a design is tapeout-ready: parse the opensynth report, check timing/DRC status, and state the signoff boundary honestly. Use after synth.py completes, or whenever asked "is it done".
---

# Signoff and GDS

## The report

```
python scripts/report.py <design_dir>          # human-readable
python scripts/report.py <design_dir> --json   # machine-readable
```

## Signoff checklist (all must hold)

1. **GDS exists** — `build/results/<platform>/<name>/base/6_final.gds`.
2. **Timing met** — `worst_slack_ns ≥ 0` (WNS/TNS `0.00` with positive slack means met).
3. **Routing DRC clean** — `drc.empty == true` (ORFS detailed-route DRC).
4. **Lint clean + sim PASS** — from the verify-rtl stage; re-run if RTL changed since.

If any check fails, the design is NOT signed off. Route to the owning skill: timing → synth-pnr, RTL/tests → verify-rtl/rtl-from-spec.

## What this signoff does and does NOT cover — be honest about this

**Covered:**
- Synthesis, floorplan, placement, CTS, routing through OpenROAD on the sky130hd library.
- Post-route timing analysis (setup and hold) with sky130hd libraries.
- Detailed-routing DRC (OpenROAD's DRC engine).
- GDSII generation (merged standard-cell GDS, `6_final.gds`).

**NOT covered in v1 (state this in any signoff summary):**
- **Full-signoff DRC/LVS** with magic/netgen against the raw sky130 PDK — ORFS runs its own DRC during routing, but a tapeout-grade run uses `magic -drc` + `netgen -lvs` on the final GDS. This is the main v1.x upgrade.
- **Antenna checks** beyond ORFS defaults.
- **Package/IO/pad frames** — designs are core-only; there is no pad ring, so this GDS is not directly bondable.
- **Formal equivalence** — the ORFS image's Kepler Formal requires AVX-512 and is disabled; equivalence rests on lint+sim.
- **IR drop / electromigration** signoff (ORFS reports exist under `reports/.../final_ir_drop.webp.png` but are advisory here).

## Output format for a signoff statement

```
SIGNOFF: <design> on <platform> — PASS|FAIL
- GDS: <path>
- Timing: worst slack <x> ns (met|VIOLATED)
- Routing DRC: clean|<n> violations
- Sim: PASS (<n> checks) | not run
- Known signoff gaps: full DRC/LVS (magic/netgen), pad ring, formal equivalence
```

A signoff statement that omits the "gaps" line is wrong, even when everything passes.
