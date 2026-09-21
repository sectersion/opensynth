"""Shared helpers for opensynth scripts (stdlib only)."""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

LINT_IMAGE = "hdlc/verilator:latest"
SIM_IMAGE = "hdlc/iverilog:latest"
ORFS_IMAGE = "openroad/orfs:latest"

TOOLS_PREFIX = ""  # hdlc images put tools on PATH


class ScriptError(Exception):
    """Fatal script error; message is shown to the user/agent as-is."""


def docker_run(image: str, mounts: list, cmd: list, workdir: str = "/work",
               timeout: int = None) -> subprocess.CompletedProcess:
    """Run a command in a docker container with host directories mounted.

    mounts: list of (host_path, container_path) tuples.
    timeout: seconds before the container is killed (None = no limit).
    """
    docker = shutil.which("docker") or shutil.which("docker.exe")
    if docker is None:
        raise ScriptError(
            "docker not found on PATH. Install Docker Desktop and ensure it is running."
        )
    if not docker.lower().endswith(".exe"):
        exe = docker + ".exe"
        if Path(exe).exists():
            docker = exe
    argv = [docker, "run", "--rm"]
    for host, container in mounts:
        host = Path(host).resolve()
        if not host.exists():
            raise ScriptError(f"mount source does not exist: {host}")
        argv += ["-v", f"{host}:{container}"]
    argv += ["-w", workdir, image] + cmd
    try:
        return subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", shell=False, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise ScriptError(
            f"docker command exceeded its {timeout}s timeout and was killed: "
            f"{image} {' '.join(cmd)}"
        )
    except FileNotFoundError:
        raise ScriptError(
            "failed to launch docker. Is Docker Desktop running? Start it and retry."
        )
    except OSError:
        # docker.exe may be a reparse point/app-execution alias on Windows;
        # fall back to invoking through cmd with the binary quoted.
        try:
            return subprocess.run(f'"{docker}" ' + " ".join(argv[1:]),
                                  capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", shell=True,
                                  timeout=timeout)
        except subprocess.TimeoutExpired:
            raise ScriptError(
                f"docker command exceeded its {timeout}s timeout and was killed: "
                f"{image} {' '.join(cmd)}"
            )
        except OSError as e:
            raise ScriptError(f"failed to launch docker: {e}")


def parse_design_yaml(path: Path) -> dict:
    """Minimal YAML subset parser for design.yaml (nested dicts, scalars, lists).

    Supports 'key: value', 'key:' followed by '  - item' lists, and comments.
    """
    if not path.exists():
        raise ScriptError(f"design spec not found: {path}")
    root: dict = {}
    stack = [(-1, root)]
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        content = line.strip()
        if content.startswith("- ") or content == "-":
            item = _scalar(content[2:].strip()) if content != "-" else None
            if isinstance(parent, list):
                parent.append(item)
            elif isinstance(parent, dict) and all(_is_int(k) for k in parent):
                # list under a key: items stored with int keys, converted by _fix_lists
                parent[str(len(parent))] = item
            else:
                raise ScriptError(f"malformed list entry in {path}: {raw!r}")
            continue
        if ":" not in content:
            raise ScriptError(f"malformed line in {path}: {raw!r}")
        key, _, value = content.partition(":")
        key, value = key.strip(), value.strip()
        if value == "":
            child: dict = {}
            parent[key] = child
            stack.append((indent, child))
            # list may follow; '- ' branch converts empty dict to list on first item
        else:
            parent[key] = _scalar(value)
    # Post-pass: convert dicts that only received list items into lists
    _fix_lists(root)
    return root


def _fix_lists(node):
    if isinstance(node, dict):
        for k, v in list(node.items()):
            if isinstance(v, dict) and v and all(_is_int(k2) for k2 in v.keys()):
                node[k] = list(v.values())
            _fix_lists(node[k] if k in node else v)


def _is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def _scalar(value: str):
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [_scalar(v.strip()) for v in inner.split(",")] if inner else []
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    return value


def load_design(design_dir: Path) -> dict:
    return parse_design_yaml(design_dir / "design.yaml")


def design_rtl_files(design_dir: Path, spec: dict) -> list:
    design_dir = design_dir.resolve()
    files = []
    for rel in spec.get("design", {}).get("rtl_sources", []):
        p = design_dir / rel
        if not p.exists():
            raise ScriptError(f"RTL source listed in design.yaml not found: {p}")
        files.append(p)
    if not files:
        raise ScriptError(
            "no rtl_sources defined in design.yaml. Add your RTL files there."
        )
    return files


def output_result(payload: dict, as_json: bool, human: str) -> None:
    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        print(human)


def add_common_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("design_dir", type=Path, help="design directory containing design.yaml")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON output")
    return parser


def fail(payload: dict, message: str, as_json: bool, exit_code: int = 1) -> int:
    payload["status"] = "fail"
    payload["error"] = message
    output_result(payload, as_json, f"FAIL: {message}")
    return exit_code
