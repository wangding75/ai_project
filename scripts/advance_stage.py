#!/usr/bin/env python3
"""
advance_stage.py — 从当前阶段推进到下一阶段

Usage:
  scripts/advance_stage.py <project>
  scripts/advance_stage.py hermes

流程：
  1. 定位 <project>/PROGRESS.md 确定当前阶段
  2. 跑 check_stage，当前阶段必须全部通过
  3. 更新 <project>/CLAUDE.md：替换"当前阶段"区块，指向下一阶段文档
  4. 跑 update_progress.py，让 PROGRESS.md 反映新状态
  5. 如果推进到阶段 04，触发 lock_tests.sh
  6. 提示用户创建 stage commit（不自动 commit，由用户确认）

失败会立即返回非零退出码。
"""
from __future__ import annotations

import sys
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_stage import check_stage, print_report  # noqa: E402


STAGE_ORDER = [
    "01-requirements",
    "02-system-design",
    "03-module-design",
    "04-development",
    "05-testing",
    "06-deployment",
    "07-operations",
]


def find_current_stage(project: str) -> str | None:
    """Scan stages in order, return the first not-yet-passed stage."""
    for stage_id in STAGE_ORDER:
        report = check_stage(project, stage_id)
        if report["status"] != "PASS":
            return stage_id
    return None


def next_stage(stage_id: str) -> str | None:
    try:
        idx = STAGE_ORDER.index(stage_id)
    except ValueError:
        return None
    if idx + 1 >= len(STAGE_ORDER):
        return None
    return STAGE_ORDER[idx + 1]


def update_claude_md(project: str, new_stage: str) -> None:
    """Replace the '当前阶段' marker in the project CLAUDE.md.

    We look for a line matching '**当前阶段：' and replace it, and we
    also rewrite the '## 当前阶段文档' block to point at the new stage dir.
    This is a best-effort textual update — user should review before commit.
    """
    claude_file = REPO_ROOT / project / "CLAUDE.md"
    if not claude_file.exists():
        print(f"WARN: {claude_file} not found, skipping update")
        return

    content = claude_file.read_text(encoding="utf-8")
    lines = content.splitlines()

    out = []
    in_stage_block = False
    replaced = False

    for line in lines:
        if line.startswith("**当前阶段：") or line.startswith("**Current Stage"):
            out.append(f"**当前阶段：{new_stage}**")
            replaced = True
            continue

        if line.startswith("## 当前阶段文档"):
            in_stage_block = True
            out.append(line)
            out.append("")
            out.append(f"进入新阶段后，请在此处手动添加 `stages/{new_stage}/` 下的关键文档引用。")
            out.append("")
            out.append(f"参考：`stages/{new_stage}/deliverables.yaml`")
            continue

        if in_stage_block:
            if line.startswith("## "):
                in_stage_block = False
                out.append(line)
            continue

        out.append(line)

    if not replaced:
        print(f"WARN: could not find '**当前阶段：' marker in {claude_file}")

    claude_file.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"✅ Updated {claude_file.relative_to(REPO_ROOT)}")


def maybe_lock_tests(project: str, new_stage: str) -> None:
    if new_stage != "04-development":
        return
    lock_script = REPO_ROOT / "scripts" / "lock_tests.sh"
    if not lock_script.exists():
        print(f"WARN: {lock_script} not found, cannot lock tests")
        return
    tests_dir = REPO_ROOT / project / "stages" / "04-development" / "tests"
    print(f"🔒 Locking {tests_dir.relative_to(REPO_ROOT)}")
    subprocess.run(["bash", str(lock_script), str(tests_dir)], check=False)


def advance(project: str) -> int:
    current = find_current_stage(project)
    if current is None:
        print(f"✅ {project} has completed all stages")
        return 0

    print(f"Current stage for {project}: {current}")
    print(f"Running check_stage to verify completion...")
    report = check_stage(project, current)
    print_report(report)

    if report["status"] != "PASS":
        print(f"\n❌ Cannot advance: {current} is not fully complete.")
        print(f"   Missing: {report['total'] - report['passed']} deliverables")
        return 1

    nxt = next_stage(current)
    if nxt is None:
        print(f"✅ {current} is the last stage. Project is complete!")
        return 0

    print(f"\n✅ {current} is complete. Advancing to {nxt}...")
    update_claude_md(project, nxt)
    maybe_lock_tests(project, nxt)

    # Regenerate PROGRESS.md
    update_script = REPO_ROOT / "scripts" / "update_progress.py"
    subprocess.run([sys.executable, str(update_script), project], check=False)

    print(f"\n📝 Review changes and create stage commit:")
    print(f"   git add {project}/CLAUDE.md {project}/PROGRESS.md")
    print(f"   git commit -m 'stage: advance {project} from {current} to {nxt}'")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    return advance(sys.argv[1])


if __name__ == "__main__":
    sys.exit(main())
