---
name: rtl-from-spec
description: Generate synthesizable SystemVerilog/Verilog RTL from a natural-language design spec, following opensynth coding rules and the sky130/ORFS flow constraints. Use when a spec.md exists but rtl/ is missing or incomplete.
---

# RTL from Spec

Turn `spec.md` into working RTL in `rtl/`. Study `examples/counter/` first — it is the golden reference for every convention below.

## Before writing any RTL

1. Read the design's `spec.md` in full. If it is ambiguous (missing reset style, clocking, edge cases), resolve ambiguity toward the simplest synchronous design and document the assumption in the RTL header comment.
2. Read `design.yaml`. The top module name **must** equal `design.name`.
3. Check whether a testbench exists in `tb/`. If yes, the testbench is the contract — the RTL must make it pass without modifying the testbench's checks.

## Where to put things

```
<design_dir>/
├── spec.md
├── design.yaml      # already exists; update rtl_sources if you add files
├── rtl/<name>.v     # one file per module
└── tb/<name>_tb.v   # see the verify-rtl skill
```

Every RTL file you add must be listed in `design.yaml` under `design.rtl_sources`.

## Synthesizable subset rules (strict)

These rules exist because the downstream flow is Yosys + OpenROAD on sky130:

- **Synchronous, single-clock designs.** One `always @(posedge clk)` style; use synchronous active-low reset (`rst_n`) unless the spec demands otherwise.
- **No latches.** Every path through a combinational `always @*` block must assign all outputs; prefer continuous `assign` where possible.
- **No initial blocks, no delays, no `$display` in RTL.** Those belong in testbenches only.
- **No vendor primitives, no tristates (except top-level IO pads, which we don't do yet), no multiple drivers.**
- **Parameterize widths** (`parameter WIDTH = 8`) rather than hardcoding — but keep the default matching the spec.
- **Avoid `signed` arithmetic and division/modulo** unless required; they synthesize poorly. Yosys handles `+`, `-`, comparisons, and shifts well.
- ** Memories (arrays) are allowed** but map to flops unless the spec says otherwise; large memories need ORFS memory configuration — flag this in the spec if you need it.
- **Register all outputs** where practical; it helps timing closure.
- File/module naming: lowercase, same name as module (`counter.v` contains `module counter`).

## Verification before declaring done

Run, from the repo root:

```
python scripts/lint.py <design_dir>
python scripts/sim.py <design_dir>
```

- **Lint must exit 0 with zero warnings** (`-Wall` is on). Fix warnings, don't suppress them.
- **Sim must print PASS.** If tests fail, fix the RTL (not the testbench — see verify-rtl skill for the exception where the *spec* changed).

## Iteration loop

If sim fails: read the FAIL lines (they include expected vs actual), form a hypothesis about the RTL, change one thing, re-run. Do not rewrite the whole module on first failure.

## Done means

1. `lint.py` exits 0, zero warnings.
2. `sim.py` exits 0.
3. `rtl_sources` in `design.yaml` lists every file you created.
4. A short comment header in each RTL file states what it implements and any spec assumptions.
