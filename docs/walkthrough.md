# Walkthrough: counter, spec to GDS

Annotated end-to-end run of `examples/counter/`, showing what each stage does and
what a *pass* looks like. Use this as the mental model for a new design; the counter
is tiny, so follow along with the real files.

The design: a parameterizable 8-bit up-counter with synchronous active-low reset,
an `enable`, and wraparound (see `examples/counter/spec.md`).

## Stage 0 — inputs already in place

```
examples/counter/
├── spec.md          # the contract: interface + numbered testable behaviors
├── design.yaml      # name=counter, rtl/counter.v, clk @ 10 ns
└── rtl/counter.v    # ~15 lines: one always @(posedge clk), sync reset
```

An agent attacking a new design generates this exact shape from
`templates/spec.template.md` + `templates/design.yaml`.

## Stage 1 — lint (seconds)

```
$ python scripts/lint.py examples/counter
LINT PASS: counter (0 warnings)
```

Verilator `--lint-only -Wall`. Any `%Warning` — widths, unused, pin wiring — fails
the run. This is deliberately strict: a warning here becomes a synth failure there.

## Stage 2 — sim (seconds)

```
$ python scripts/sim.py examples/counter
SIM PASS: 1 testbench(es) passed
```

`tb/counter_tb.v` is self-checking: it drives reset/enable/wraparound sequences,
computes the expected count independently, and prints `PASS:` only if every
`(expected, actual)` pair matched. Exit 0 = all testbenches passed.

## Stage 3 — synthesis + P&R (10–45 min first run)

```
$ python scripts/synth.py examples/counter
ORFS PASS: counter on sky130hd -> examples/counter/build/results/sky130hd/counter/base/6_final.gds
```

What happens under the hood (all inside docker, driven entirely by the script):

1. `scripts/synth.py` renders `build/design/config.mk` (ORFS design config) and
   `build/design/constraint.sdc` (100 MHz clock, input/output delay at 20% of
   period) from `design.yaml`. Your RTL is copied into `build/design/rtl/`.
2. The ORFS make flow runs: yosys synthesis → floorplan → CTS (with
   `SKIP_CTS_REPAIR_TIMING=1`, see skill synth-pnr) → place → detailed route →
   fillcells → GDS merge.
3. Artifacts: `build/results/.../6_final.gds` (the deliverable),
   `build/reports/.../` (timing/DRC reports), `build/logs/.../` (stages).

## Stage 4 — signoff (seconds)

```
$ python scripts/report.py examples/counter

DESIGN REPORT: counter (sky130hd)
  GDS:           examples\counter\build\results\sky130hd\counter\base\6_final.gds
  Worst slack:   6.85 ns   WNS: 0.00 ns   TNS: 0.00 ns
  Min period:    1.28 ns  (fmax ~779.0 MHz)
  Area:          474 um^2, 37 cells
  Routing DRC:   clean (0 violations)
  Signoff gates: PASS
```

`--check` (or exit code) is the machine gate: 0 iff GDS exists ∧ `worst slack ≥ 0` ∧
zero routing DRC violations. Numbers above are from an actual run on this repo — a
glass bucket at 100 MHz with wide margin, as expected.

The signoff statement is *not* fully automatic: a human-readable summary must still
state what's unresolved (full DRC/LVS, pad ring, formal equivalence). See
`skills/signoff-gds/SKILL.md` for the format — skipping the gaps line makes signoff
incomplete even when all checks pass.

## What changes for a new design

Everything above is identical; only the inputs change. The workflow checklist:

1. `spec.md` numbered behaviors, testable.
2. `design.yaml`: correct `name` (equals top module), `rtl_sources` listing every
   file you wrote, `clock_period_ns` from the spec's timing target.
3. Lint → sim → synth → `report --check`. Repeat one fix at a time on any failure.
