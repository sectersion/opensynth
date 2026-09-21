---
name: verify-rtl
description: Write and run self-checking testbenches for opensynth designs; interpret lint and simulation failures. Use when creating or debugging tests in tb/.
---

# Verify RTL

Owns everything in `tb/` and the lint/sim loop.

## Testbench conventions (mandatory)

Study `examples/counter/tb/counter_tb.v` — it is the canonical shape:

- **Self-checking**: the TB computes expected values (reference model) and compares against DUT outputs every cycle. It never relies on human waveform inspection.
- **PASS/FAIL contract**: on success print exactly `PASS: ...` as the final line; on failure print `FAIL: ...`, increment an `errors` counter, and end with `$fatal(1, ...)`. `scripts/sim.py` greps for a line starting with `PASS` and treats nonzero exit as failure — follow both contracts.
- **No golden vectors files, no PLI, no external dependencies.** Pure iverilog, `-g2012`.
- Check on the negedge of the clock (avoids race with posedge DUT updates).
- Cover the interesting cases: reset behavior, enable/disable, wraparound/overflow, boundary values, back-to-back operations. At minimum: reset → normal operation → hold/pause → reset again.

## Running

```
python scripts/lint.py <design_dir>   # must be clean BEFORE sim
python scripts/sim.py <design_dir>    # runs every tb/*.v
python scripts/sim.py <design_dir> --tb tb/my_tb.v   # single testbench
```

Lint warnings are errors in this flow. `WIDTHEXPAND`/`WIDTHTRUNC` usually mean an arithmetic bug or a too-narrow port — fix the RTL, don't silence the warning.

## Reading failures

- `FAIL: count=x expected=0 @0` — checked before a clock edge; move the first check after a negedge, or reset the model too.
- `count=x` where x is X — uninitialized flop: missing reset of a register, or checking before the first clock edge.
- `$fatal` with no FAIL lines — the TB itself crashed; look for unsupported iverilog constructs.
- Timeout (vvp never exits) — missing `$finish`, or a `wait`/`@` that never fires.

## Who gets fixed

- If the **RTL** deviates from `spec.md` → fix the RTL (see rtl-from-spec skill).
- If the **testbench** deviates from `spec.md` (wrong expected values, wrong protocol) → fix the testbench. State the reason in the commit/summary.
- If **spec.md** itself is self-contradictory → fix the spec first, then realign RTL and TB, and flag the change to the user.

## Done means

1. `sim.py` exits 0, every testbench in `tb/` passes.
2. The testbench covers reset, normal operation, and at least one edge case from the spec.
