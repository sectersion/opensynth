# Contributing to opensynth

## Project layout at a glance

- `AGENTS.md` — the contract coding agents follow; keep it accurate whenever a rule
  or exit code changes.
- `skills/` — short playbooks the agent reads per-stage. `SKILL.md` frontmatter
  `description` is the routing trigger; keep it specific.
- `scripts/` — the only path to the EDA tools. Stdlib-only Python, no deps.
- `tests/` — selfcheck: unit tests + docker-backed smoke tests
  (`python tests/test_scripts.py`; docker tests skip gracefully when unavailable).

## Ground rules

1. **Scripts are the contract.** Exit codes (0/1/2) and `--json` payloads are consumed
   by agents and scripts alike — changing either shape requires updating `AGENTS.md`,
   `README.md`, and `tests/test_scripts.py` in the same change.
2. **Never weaken a gate** (`report.py --check`, lint-warning failures, sim `FAIL`
   detection) without stating why in the PR and updating the docs that reference it.
3. **Docs travel together.** A behavior change in scripts needs matching updates in
   the relevant `skills/*/SKILL.md`, `AGENTS.md`, and `README.md`.

## Local checks before opening a PR

```powershell
python tests/test_scripts.py        # unit + docker smoke tests
python scripts/lint.py  examples/counter
python scripts/sim.py   examples/counter
```

Synthesis (`synth.py`) is heavy (~6.5GB image, 10–45 min); run it only when your
change affects the physical flow, and use `--stage synth` for quick iterations.

## Commit style

Short, imperative subject; mention the stage(s) touched. Docs-only changes are fine
but should still pass the selfcheck if any file it reads changed.
