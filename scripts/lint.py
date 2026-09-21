"""Lint RTL with Verilator (--lint-only) inside docker.

Usage: python scripts/lint.py <design_dir> [--json]
Exit codes: 0 = lint clean, 1 = lint errors, 2 = setup error.
"""

import argparse
import sys

from _common import (
    LINT_IMAGE,
    REPO_ROOT,
    TOOLS_PREFIX,
    ScriptError,
    add_common_args,
    design_rtl_files,
    docker_run,
    fail,
    load_design,
    output_result,
)


def main() -> int:
    parser = add_common_args(argparse.ArgumentParser(description=__doc__))
    args = parser.parse_args()
    payload = {"stage": "lint", "design_dir": str(args.design_dir)}
    as_json = args.json

    try:
        spec = load_design(args.design_dir)
        rtl_files = design_rtl_files(args.design_dir, spec)
        top = spec.get("design", {}).get("name")
        if not top:
            raise ScriptError("design.name missing in design.yaml")

        # Mount design dir and a scratch build dir; verilator writes nothing on --lint-only.
        container_files = [f"/work/{f.relative_to(args.design_dir.resolve()).as_posix()}" for f in rtl_files]
        proc = docker_run(
            LINT_IMAGE,
            mounts=[(args.design_dir, "/work")],
            cmd=[TOOLS_PREFIX + "verilator", "--lint-only", "-Wall",
                 "--top-module", top] + container_files,
            timeout=120,
        )
    except ScriptError as e:
        return fail(payload, str(e), as_json, exit_code=2)

    warnings = [l for l in proc.stderr.splitlines() if l.startswith("%Warning")]
    errors = [l for l in proc.stderr.splitlines() if l.startswith("%Error")]
    payload.update({
        "returncode": proc.returncode,
        "warnings": warnings,
        "errors": errors,
        # -Wall: warnings are violations too (AGENTS.md: lint done = 0 warnings)
        "status": "pass" if proc.returncode == 0 and not errors and not warnings else "fail",
    })
    if payload["status"] == "pass":
        output_result(payload, as_json, f"LINT PASS: {top} (0 warnings)")
        return 0

    output_result(payload, as_json,
                  "LINT FAIL:\n" + "\n".join(errors + warnings))
    return 1


if __name__ == "__main__":
    sys.exit(main())
