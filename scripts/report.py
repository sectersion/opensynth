"""Summarize ORFS results for a design: timing, area, DRC, GDS path.

Usage: python scripts/report.py <design_dir> [--json]

Reads build/reports/ and build/results/ written by scripts/synth.py.
Exit codes: 0 = report generated and --check gates pass (if used),
1 = --check gate failure, 2 = setup error (no results found).
"""

import argparse
import json
import re
import sys

from _common import (
    ScriptError,
    add_common_args,
    fail,
    load_design,
    output_result,
)


def read_report(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def grab(text, pattern, default=None):
    m = re.search(pattern, text, re.M)
    return m.group(1) if m else default


def _slack_ok(finish_text) -> bool:
    """True if worst slack was parsed and is >= 0."""
    slack = grab(finish_text, r"worst slack max ([\d.-]+)")
    if slack is None:
        return False
    try:
        return float(slack) >= 0.0
    except ValueError:
        return False


def main() -> int:
    parser = add_common_args(argparse.ArgumentParser(description=__doc__))
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if signoff gates fail (negative slack or DRC violations)")
    args = parser.parse_args()
    as_json = args.json

    try:
        spec = load_design(args.design_dir)
        name = spec.get("design", {}).get("name")
        platform = spec.get("design", {}).get("platform", "sky130hd")
        if not name:
            raise ScriptError("design.name missing in design.yaml")
    except ScriptError as e:
        return fail({"stage": "report"}, str(e), as_json, exit_code=2)

    base = args.design_dir / "build"
    reports = base / "reports" / platform / name / "base"
    results = base / "results" / platform / name / "base"
    logs = base / "logs" / platform / name / "base"

    if not results.exists():
        return fail({"stage": "report", "design_dir": str(args.design_dir)},
                    f"no ORFS results found under {results}. "
                    "Run scripts/synth.py first.", as_json, exit_code=2)

    finish = read_report(reports / "6_finish.rpt")
    drc = read_report(reports / "5_route_drc.rpt")
    synth_stat = read_report(reports / "synth_stat.txt")
    # area is reported in the detailed-route / fillcell stage log
    drt_log = read_report(logs / "5_3_fillcell.log")

    gds = results / "6_final.gds"
    yosys_log = read_report(reports / "synth_stat.txt")
    cell_count = grab(yosys_log, r"^\s*(\d+)\s+[\d.]+\s+\d+\s+[\d.]+\s+cells", None)
    area = grab(drt_log, r"Design area ([\d.]+) um\^2")

    payload = {
        "stage": "report",
        "design": name,
        "platform": platform,
        "status": "pass" if gds.exists() else "fail",
        "gds": str(gds) if gds.exists() else None,
        "timing": {
            "wns_ns": grab(finish, r"wns max ([\d.-]+)"),
            "tns_ns": grab(finish, r"tns max ([\d.-]+)"),
            "worst_slack_ns": grab(finish, r"worst slack max ([\d.-]+)"),
            "min_period_ns": grab(finish, r"period_min = ([\d.]+)"),
            "fmax_mhz": grab(finish, r"fmax = ([\d.]+)"),
        },
        "area": {
            "design_area_um2": area,
            "cell_count": cell_count,
        },
        "drc": {
            "violations_report": str(reports / "5_route_drc.rpt"),
            "empty": drc.strip() == "",
        },
        "checks": {  # machine-readable signoff gates (used by --check)
            "gds_exists": gds.exists(),
            "slack_ok": _slack_ok(finish),
            "drc_clean": drc.strip() == "",
        },
        "notes": [
            "wns/tns of 0.00 with positive worst_slack means timing is met.",
            "drc.empty == True means zero routing DRC violations.",
            "Full OpenROAD GUI-quality DRC/LVS against the PDK is a follow-up "
            "(see skills/signoff-gds).",
        ],
    }

    gates = payload["checks"]
    all_pass = all(gates.values())

    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        t, a = payload["timing"], payload["area"]
        lines = [
            f"DESIGN REPORT: {name} ({platform})",
            f"  GDS:           {payload['gds'] or 'NOT FOUND'}",
            f"  Worst slack:   {t['worst_slack_ns']} ns   WNS: {t['wns_ns']} ns   TNS: {t['tns_ns']} ns",
            f"  Min period:    {t['min_period_ns']} ns  (fmax ~{t['fmax_mhz']} MHz)",
            f"  Area:          {a['design_area_um2']} um^2, {a['cell_count']} cells",
            f"  Routing DRC:   {'clean (0 violations)' if payload['drc']['empty'] else 'VIOLATIONS - see ' + payload['drc']['violations_report']}",
        ]
        failed = [k for k, ok in gates.items() if not ok]
        if failed:
            lines.append(f"  Signoff gates: FAILED ({', '.join(failed)})")
        elif args.check:
            lines.append("  Signoff gates: PASS")
        print("\n".join(lines))

    if args.check and not all_pass:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
