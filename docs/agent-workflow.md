# Agent workflow — how to run opensynth as an agent

This is the deeper "how to *behave*" guide, complementing `AGENTS.md` (the contract)
and the individual `skills/` playbooks (how to execute each stage). Read this once
at the start of a session on a design.

## Who you are here

You are the orchestrator and the engineer. The scripts are your lab equipment: each
one is deterministic, fast-failing, and exits with a code from a small set:

| Exit | Meaning | Your reaction |
|---|---|---|
| `0` | Stage succeeded | Move to the next stage |
| `1` | Design problem (RTL bug, test failure, timing violation, DRC) | Read the output, form *one* hypothesis, fix, re-run |
| `2` | Environment/setup problem (docker down, missing files) | Fix the setup; do not touch the design |

Never treat `2` as a design bug, and never treat `1` as an environment bug. Check
`docker info` works *before* concluding anything from a `2`.

## Always use `--json`

The scripts' human output is convenience; the `--json` output is the contract. As an
agent, run with `--json` and parse:

```
lint.py  --json  -> {status, warnings[], errors[], returncode}
sim.py   --json  -> {suites[{testbench, passed, returncode, log[]}], status}
synth.py --json  -> {status, gds, log_tail[], returncode}
report.py --json -> {timing{...}, area{...}, drc{...}, checks{gds_exists, slack_ok, drc_clean}}
```

`report.py --json` also exposes `checks` — the machine-readable signoff gates. When
checking "is it done", read `checks`, never eyeball the report prose. Deterministic
gates (`report.py --check`, exit 1 unless clean) exist precisely so you don't have to
interpret prose.

## Stage discipline

1. **Never skip stages.** Lint before sim every iteration, lint+sim before every synth.
   A synth run costs 10–45 minutes; a lint run costs seconds. A synth failure caused by
   a lint-catchable mistake wasted the expensive run.
2. **One hypothesis per run.** Change one thing (RTL line, one yaml knob, one constraint),
   re-run the cheapest script that can validate it, and read the failure completely before
   the next change. Debugging by shotgun edits wastes an entire synth cycle per guess.
3. **Cheapest verification first.** Classic order after a synth failure:
   `lint.py` (seconds) → re-`sim.py` (seconds) → read `reports/` (instant) →
   re-run `synth.py --stage synth` (~1 min) → full flow (last resort).
4. **State lives in the design directory.** Never edit `build/` (generated). The human
   interface to design intent is `spec.md`; the machine interface is `design.yaml`.
   Everything an agent "decides" must land in one of those two artifacts (or a `.v`).

## The three files you must never fudge

| File | Rule |
|---|---|
| `tb/*.v` | The testbench is the contract. Never weaken checks to make RTL pass. |
| `timing.clock_period_ns` (design.yaml) | A spec-derived period is never loosened to hide structural timing violations. |
| `rtl/` vs spec | RTL matching `spec.md` is the goal; if the spec was wrong, change the spec *and* state that you did. |

Tests and skill doc strings exist to make these rules inconvenient to violate — use
that friction instead of talking yourself past it.

## Reading failures the productive way

- **Sim FAIL with expected/actual**: the diff usually names the *first divergent
  stimulus* — which "Behavior" numbered statement does it violate? Fix to make that
  specific statement true; don't rewrite the module.
- **Lint warnings**: `WIDTHEXPAND`/`WIDTHTRUNC` → arithmetic or port-width bug, not
  noise. `UNUSEDSIGNAL` → dead code or a stub you meant to connect. `PINMISSING` →
  module instance wiring bug. Fix RTL, never suppress.
- **Synth/router errors**: read the `log_tail` synth.py prints first; per-stage logs
  under `build/logs/<platform>/<name>/base/` are the ground truth.
- **`worst slack` slightly negative** (> −0.2 ns) may vanish on re-run — placement is
  stochastic. Persistent negative slack is an RTL problem (long combinational paths);
  pipeline or retime rather than relaxing the constraint arbitrarily.

## Working as a subagent / on a fresh clone

1. Read `AGENTS.md` (this file is pointed to from it), then the skills for exactly the
   stages you will touch. Skills are short — read at least the "Done means" section so
   you know when to stop.
2. Verify the environment *once* per session: `docker info` succeeds, then let
   `lint.py`/`sim.py` pull their images automatically on first run (~100MB–1GB each;
   the ORFS image is ~6.5GB — run it only when you need it).
3. See `docs/walkthrough.md` for what a successful full run looks like at every stage,
   and `tests/test_scripts.py` for scripted examples of fail/malformed cases.
