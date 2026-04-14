#!/usr/bin/env python3
"""
check_stage.py — 验证某个项目的某个阶段是否满足 deliverables.yaml 定义的产出清单

Usage:
  scripts/check_stage.py <project> <stage-id>
  scripts/check_stage.py hermes 03-module-design

Exit codes:
  0 = all deliverables met
  1 = one or more deliverables missing
  2 = usage error / config error
"""
from __future__ import annotations

import os
import sys
import subprocess
import fnmatch
import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parent.parent


def check_file(spec: dict, stage_dir: Path) -> tuple[bool, str]:
    path = stage_dir / spec["path"]
    if not path.exists():
        return False, f"file not found: {path.relative_to(REPO_ROOT)}"
    if not path.is_file():
        return False, f"not a file: {path.relative_to(REPO_ROOT)}"

    if "min_size_bytes" in spec:
        size = path.stat().st_size
        if size < spec["min_size_bytes"]:
            return False, f"file too small: {size} < {spec['min_size_bytes']} bytes"

    if "must_contain" in spec:
        content = path.read_text(encoding="utf-8", errors="ignore")
        missing = [s for s in spec["must_contain"] if s not in content]
        if missing:
            return False, f"missing required sections: {missing}"

    return True, "ok"


def check_dir(spec: dict, stage_dir: Path) -> tuple[bool, str]:
    path = stage_dir / spec["path"]
    if not path.exists():
        return False, f"dir not found: {path.relative_to(REPO_ROOT)}"
    if not path.is_dir():
        return False, f"not a dir: {path.relative_to(REPO_ROOT)}"

    pattern = spec.get("pattern", "*")
    files = [f for f in path.rglob("*") if f.is_file() and fnmatch.fnmatch(f.name, pattern)]

    if "min_files" in spec:
        if len(files) < spec["min_files"]:
            return False, f"too few files: {len(files)} < {spec['min_files']} (pattern={pattern})"

    return True, f"ok ({len(files)} files)"


def check_command(spec: dict, stage_dir: Path) -> tuple[bool, str]:
    cmd = spec["cmd"]
    cwd = stage_dir if spec.get("cwd_stage", True) else REPO_ROOT
    expect_exit = spec.get("expect_exit_code", 0)

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return False, f"command timed out: {cmd}"

    if result.returncode != expect_exit:
        stderr = result.stderr.strip()[:200]
        return False, f"exit={result.returncode} (expected {expect_exit}): {stderr}"

    return True, f"ok (exit={result.returncode})"


def check_files_patterns(spec: dict, stage_dir: Path) -> tuple[bool, str]:
    """Check that files matching ALL of the given patterns exist."""
    base = stage_dir / spec["path"]
    if not base.exists():
        return False, f"base dir not found: {base.relative_to(REPO_ROOT)}"

    patterns = spec["patterns"]
    missing = []
    for pat in patterns:
        matches = [f for f in base.rglob("*") if f.is_file() and fnmatch.fnmatch(f.name, pat)]
        if not matches:
            missing.append(pat)

    if missing:
        return False, f"no files matching patterns: {missing}"
    return True, f"ok (all {len(patterns)} patterns matched)"


def check_git(spec: dict, stage_dir: Path) -> tuple[bool, str]:
    """Check git log for a commit matching a pattern."""
    pattern = spec["must_exist"]
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", f"--grep={pattern}", "-E"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return False, "git log timed out"

    if result.returncode != 0:
        return False, f"git log failed: {result.stderr.strip()}"
    if not result.stdout.strip():
        return False, f"no commit matching: {pattern}"
    return True, f"ok (commit found)"


CHECKERS = {
    "file": check_file,
    "dir": check_dir,
    "command": check_command,
    "files": check_files_patterns,
    "git": check_git,
}


def check_stage(project: str, stage_id: str) -> dict:
    """Run all deliverable checks for a stage. Returns a result dict."""
    stage_dir = REPO_ROOT / project / "stages" / stage_id
    manifest = stage_dir / "deliverables.yaml"

    if not manifest.exists():
        return {
            "project": project,
            "stage": stage_id,
            "status": "NO_MANIFEST",
            "total": 0,
            "passed": 0,
            "results": [],
            "error": f"deliverables.yaml not found at {manifest.relative_to(REPO_ROOT)}",
        }

    with open(manifest, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    deliverables = config.get("deliverables", [])
    extra_checks = config.get("checks", [])
    all_items = deliverables + extra_checks

    results = []
    passed = 0
    for item in all_items:
        item_type = item.get("type", "command" if "cmd" in item else "unknown")
        checker = CHECKERS.get(item_type)
        if checker is None:
            results.append({
                "id": item.get("id", "<unnamed>"),
                "type": item_type,
                "ok": False,
                "message": f"unknown deliverable type: {item_type}",
            })
            continue

        try:
            ok, msg = checker(item, stage_dir)
        except Exception as e:
            ok, msg = False, f"checker error: {e}"

        results.append({
            "id": item.get("id", "<unnamed>"),
            "type": item_type,
            "ok": ok,
            "message": msg,
        })
        if ok:
            passed += 1

    total = len(all_items)
    status = "PASS" if passed == total and total > 0 else "FAIL" if total > 0 else "EMPTY"

    return {
        "project": project,
        "stage": stage_id,
        "name": config.get("name", stage_id),
        "status": status,
        "total": total,
        "passed": passed,
        "results": results,
    }


def print_report(report: dict) -> None:
    status = report["status"]
    icon = {"PASS": "✅", "FAIL": "❌", "EMPTY": "⚠️", "NO_MANIFEST": "❓"}.get(status, "?")
    print(f"\n{icon} [{report['project']}/{report['stage']}] {report.get('name', '')} — {status}")
    print(f"   {report['passed']}/{report['total']} deliverables met")

    if "error" in report:
        print(f"   ERROR: {report['error']}")
        return

    for r in report["results"]:
        icon = "✓" if r["ok"] else "✗"
        print(f"   {icon} {r['id']:30s} {r['message']}")


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2

    project = sys.argv[1]
    stage_id = sys.argv[2]
    json_output = "--json" in sys.argv

    report = check_stage(project, stage_id)

    if json_output:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_report(report)

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
