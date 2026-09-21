---
name: debug-env
description: Diagnose and fix environment/setup problems in opensynth - docker unavailable, missing or oversized images, stuck or timed-out runs, stale build artifacts. Use when a script exits with code 2, hangs, or fails before doing any design work.
---

# Debug the Environment

Exit code **2** means setup, not design. Fix the environment first; touching RTL or
constraints in response to a `2` is always wrong.

## Never blocked: the tiered fix order

Most opensynth failures that get flamed "the flow is broken" are one of these, in
roughly this frequency order. Work top-down, cheapest fix first.

### 1. Docker daemon down (exit 2, every script)

`docker info` — if that fails: start Docker Desktop, wait ~30s, retry.
On Windows, a docker alias/reparse-point quirk can confuse launching; the
`scripts/_common.py::docker_run` helper handles that, but a daemon that *is* reachable but
not responding also falls into this class.

### 2. Image not present (exit 2 on first use of a stage)

`docker images` should show `hdlc/verilator`, `hdlc/iverilog`, `openroad/orfs`.
Image pulls happen automatically on first use of each script:

- lint → `hdlc/verilator`  (~1 GB)
- sim  → `hdlc/iverilog`   (~300 MB)
- synth → `openroad/orfs`  (~6.5 GB — pull before the first synth, don't wait for the script)

Manual pull if the automated path failed: `docker pull <image>`. If sizes above
differ wildly from these, suspect a partial pull: `docker rmi` then `docker pull` again.

### 3. Stale build artifacts

`build/` outside a fresh mount or a synth.py crash mid-run can leave the next run
misbehaving. Delete `build/` and regenerate it: it is fully derived from `design.yaml`
+ `rtl/` and thus disposable. **`build/` is the ONLY thing you delete here** — rtl/,
tb/, spec.md, design.yaml are hand-written inputs.

### 4. Timed-out runs

Each script enforces a container timeout and reports it:

- lint 120 s, sim 300 s — generous for any sane RTL/TB. A timeout here means an
  infinite loop without `$finish`, or a runaway `while` with no clock check in the
  testbench. The RTL/TB is still the bug.
- synth 3 hours. Truthful full-flow runs on small designs finish in well under an
  hour; mid-size designs genuinely need more. If synth times out on a design that
  a prior run completed, suspect image/disk; re-verify `docker images`.

### 5. Small-die / PDN issues (exit 1 from synth)

`PDN-0185 Insufficient width ... straps` means the core is too small for the default
met4/met5 strap grid. `scripts/synth.py` already substitutes a met1/met2 small-die
PDN (`scripts/pdn_small.tcl`) automatically. If it still appears on a retry, the
design may simply be *too small to route* — see skill synth-pnr.

## When to escalate to a human

- Docker operating normally but image pulls hit network/auth failures you can't resolve.
- The ORFS image misbehaves beyond the documented workarounds (AVX-512 LEC,
  CTS repair_timing) already applied by the scripts.
- A disk/permission problem under `build/`.

## Applying your findings

Environment fixes are *not committed to any design* — nothing in `specs/specs/`,
`rtl/`, `tb/`, or `design.yaml` should change. If fixing the environment required
changing a `.v` or `.yaml`, the environment was *not* the original problem.
