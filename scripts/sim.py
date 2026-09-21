"""Run the design's testbench with iverilog inside docker.

Usage: python scripts/sim.py <design_dir> [--json]
Convention: testbench must print a line starting with PASS, must not
print any line starting with FAIL, and must finish via $finish within
the 300s timeout; on failure it should exit nonzero ($fatal).

Exit codes: 0 = all tests pass, 1 = tests fail, 2 = setup error.
"""

import argparse
import re
import sys

from _common import (
    REPO_ROOT,
    SIM_IMAGE,
    TOOLS_PREFIX,
    ScriptError,
    add_common_args,
    design_rtl_files,
    docker_run,
    fail,
    load_design,
    output_result,
)


def find_testbench(design_dir) -> list:
    tb_dir = design_dir / "tb"
    if not tb_dir.is_dir():
        raise ScriptError(
            f"no tb/ directory in {design_dir}. See skills/verify-rtl for the "
            "self-checking testbench convention."
        )
    tb_files = sorted(p for p in tb_dir.iterdir() if p.suffix in (".v", ".sv"))
    if not tb_files:
        raise ScriptError(
            f"no testbench files (*.v/*.sv) found in {tb_dir}. "
            "See skills/verify-rtl for the self-checking testbench convention."
        )
    return tb_files


def main() -> int:
    parser = add_common_args(argparse.ArgumentParser(description=__doc__))
    parser.add_argument("--tb", type=str, default=None,
                        help="specific testbench file (default: run all in tb/)")
    args = parser.parse_args()
    payload = {"stage": "sim", "design_dir": str(args.design_dir), "suites": []}
    as_json = args.json

    try:
        spec = load_design(args.design_dir)
        rtl_files = design_rtl_files(args.design_dir, spec)
        tb_files = [args.design_dir / args.tb] if args.tb else find_testbench(args.design_dir)
    except ScriptError as e:
        return fail(payload, str(e), as_json, exit_code=2)

    overall = "pass"
    design_dir = args.design_dir.resolve()
    for tb in tb_files:
        tb_rel = tb.resolve().relative_to(design_dir).as_posix()
        rtl_rels = [f.resolve().relative_to(design_dir).as_posix() for f in rtl_files]
        sim_cmd = (f"{TOOLS_PREFIX}iverilog -g2012 -o /tmp/sim.vvp "
                   f"{' '.join(rtl_rels + [tb_rel])} && {TOOLS_PREFIX}vvp /tmp/sim.vvp")
        proc = docker_run(
            SIM_IMAGE,
            mounts=[(args.design_dir, "/work")],
            cmd=["sh", "-c", sim_cmd],
            timeout=300,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        passed = (proc.returncode == 0
                  and re.search(r"^PASS\b", output, re.M) is not None
                  and re.search(r"^FAIL\b", output, re.M) is None)
        suite = {
            "testbench": tb_rel,
            "returncode": proc.returncode,
            "passed": passed,
            "log": output.strip().splitlines()[-40:],
        }
        payload["suites"].append(suite)
        if not passed:
            overall = "fail"

    payload["status"] = overall
    if overall == "pass":
        output_result(payload, as_json,
                      f"SIM PASS: {len(payload['suites'])} testbench(es) passed")
        return 0

    lines = ["SIM FAIL:"]
    for s in payload["suites"]:
        if not s["passed"]:
            lines.append(f"--- {s['testbench']} (rc={s['returncode']}) ---")
            lines.extend(s["log"])
    output_result(payload, as_json, "\n".join(lines))
    return 1


if __name__ == "__main__":
    sys.exit(main())
