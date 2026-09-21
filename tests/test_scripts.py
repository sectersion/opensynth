#!/usr/bin/env python3
"""Selfcheck suite for opensynth scripts.

Runs pure-Python unit checks plus docker-backed smoke tests against
examples/counter and known-bad fixtures. Docker tests are skipped
(designated as such in the summary) when the daemon is unreachable.

Usage: python tests/test_scripts.py
Exit:  0 = all non-skipped checks pass, 1 = failures.
"""

import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import _common  # noqa: E402

results = []


def check(name, ok, note=""):
    results.append((name, ok, note))
    print(f"{'PASS' if ok else 'FAIL'}: {name}" + (f" ({note})" if note else ""))


def run(args, workdir=REPO, timeout=600):
    return subprocess.run(
        [sys.executable] + args, cwd=workdir, capture_output=True, text=True,
        errors="replace", timeout=timeout,
    )


def docker_available():
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0


# --- pure-python: yaml parser ---
def test_yaml_parser():
    spec = _common.parse_design_yaml(REPO / "examples/counter/design.yaml")
    check("yaml: counter name", spec["design"]["name"] == "counter")
    check("yaml: rtl_sources is list",
          spec["design"]["rtl_sources"] == ["rtl/counter.v"])
    check("yaml: clock_period_ns int", spec["timing"]["clock_period_ns"] == 10)

    tpl = _common.parse_design_yaml(REPO / "templates/design.yaml")
    check("yaml: template parses", tpl["design"]["name"] == "mydesign")


# --- pure-python: report regex helpers ---
def test_report_helpers():
    import importlib.util
    rs = importlib.util.spec_from_file_location(
        "report", REPO / "scripts" / "report.py")
    # main() isn't importable as a package; just import module
    report = importlib.util.module_from_spec(rs)
    rs.loader.exec_module(report)

    good = "worst slack max 0.123\nperiod_min = 9.5\nfmax = 105.2"
    bad = "-0.42" if False else "worst slack max -0.42"
    none = "no slack line here"
    check("report: slack_ok parses positive", report._slack_ok(good) is True)
    check("report: slack_ok fails negative", report._slack_ok(bad) is False)
    check("report: slack_ok fails missing", report._slack_ok(none) is False)
    check("report: grab", report.grab(good, r"period_min = ([\d.]+)") == "9.5")


# --- docker-backed smoke tests ---
def test_lint_counter():
    proc = run(["scripts/lint.py", str(REPO / "examples/counter")])
    check("lint: counter exits 0", proc.returncode == 0,
          f"rc={proc.returncode}")


def test_sim_counter():
    proc = run(["scripts/sim.py", str(REPO / "examples/counter")])
    check("sim: counter exits 0", proc.returncode == 0, f"rc={proc.returncode}")


def test_sim_fail_fixture():
    proc = run(["scripts/sim.py", str(REPO / "tests/fixtures/sim_fail")])
    check("sim: FAIL fixture exits 1", proc.returncode == 1,
          f"rc={proc.returncode}")


def test_sim_no_tb_fixture():
    proc = run(["scripts/sim.py", str(REPO / "tests/fixtures/no_tb")])
    check("sim: no-tb fixture exits 2", proc.returncode == 2,
          f"rc={proc.returncode}")


def test_lint_warning_fixture():
    proc = run(["scripts/lint.py", str(REPO / "tests/fixtures/lint_fail")])
    check("lint: warning fixture exits 1 (fail on warnings)",
          proc.returncode == 1, f"rc={proc.returncode}")


def test_report_no_results():
    # a design dir with design.yaml but never synthesized -> exit 2
    proc = run(["scripts/report.py", str(REPO / "tests/fixtures/no_tb"),
                "--json"])
    check("report: no-results fixture exits 2", proc.returncode == 2,
          f"rc={proc.returncode}")


def main() -> int:
    test_yaml_parser()
    test_report_helpers()

    have_docker = docker_available()
    docker_tests = [
        test_lint_counter,
        test_sim_counter,
        test_sim_fail_fixture,
        test_sim_no_tb_fixture,
        test_lint_warning_fixture,
        test_report_no_results,
    ]
    if have_docker:
        for t in docker_tests:
            t()
    else:
        for t in docker_tests:
            check(t.__name__, True, "SKIPPED (docker unavailable)")

    failed = [(n, note) for n, ok, note in results if not ok]
    skipped = sum(1 for n, _, note in results if "SKIPPED" in note)
    print(f"\n{len(results)} checks, "
          f"{len(results) - len(failed) - skipped} passed, "
          f"{len(failed)} failed, {skipped} skipped")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
