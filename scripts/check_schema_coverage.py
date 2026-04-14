#!/usr/bin/env python3
"""
check_schema_coverage.py — 验证 TDD 测试文件覆盖了 schemas/ 中定义的所有接口契约

Usage:
  scripts/check_schema_coverage.py <project>
  scripts/check_schema_coverage.py hermes

规则：
  1. 扫描 <project>/stages/03-module-design/schemas/*.py，提取所有 Pydantic model 类名和字段
  2. 扫描 <project>/stages/04-development/tests/*.py，检查每个 schema 类名是否被 import 或引用
  3. 扫描错误码常量（ClassNameErrors.XXX）是否在测试中出现
  4. 报告覆盖差异

这不是完美的静态分析，但足以发现"忘记测试某个模块"的问题。
"""
from __future__ import annotations

import sys
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

PYDANTIC_CLASS_RE = re.compile(r"^class\s+(\w+)\s*\(\s*BaseModel\s*\)", re.MULTILINE)
ERROR_CLASS_RE = re.compile(r"^class\s+(\w+Errors)\s*:", re.MULTILINE)
ERROR_CONST_RE = re.compile(r"^\s+([A-Z_]+)\s*=", re.MULTILINE)


def extract_schemas(schemas_dir: Path) -> dict:
    """Extract all Pydantic models and error constants from schemas/ dir."""
    models: set[str] = set()
    errors: dict[str, list[str]] = {}

    for py_file in schemas_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        content = py_file.read_text(encoding="utf-8")

        for m in PYDANTIC_CLASS_RE.finditer(content):
            models.add(m.group(1))

        for m in ERROR_CLASS_RE.finditer(content):
            class_name = m.group(1)
            # find constants within this class (simple heuristic: next non-empty lines indented)
            class_start = m.end()
            next_class = content.find("\nclass ", class_start)
            class_body = content[class_start:next_class] if next_class > 0 else content[class_start:]
            consts = [c.group(1) for c in ERROR_CONST_RE.finditer(class_body)]
            if consts:
                errors[class_name] = consts

    return {"models": models, "errors": errors}


def extract_test_references(tests_dir: Path) -> str:
    """Read all test files and return concatenated content for simple substring checks."""
    content_parts = []
    for py_file in tests_dir.rglob("test_*.py"):
        content_parts.append(py_file.read_text(encoding="utf-8"))
    return "\n".join(content_parts)


def check_coverage(project: str) -> int:
    schemas_dir = REPO_ROOT / project / "stages" / "03-module-design" / "schemas"
    tests_dir = REPO_ROOT / project / "stages" / "04-development" / "tests"

    if not schemas_dir.exists():
        print(f"⚠️  schemas dir not found: {schemas_dir.relative_to(REPO_ROOT)}")
        print("    (stage 03 not yet started or schemas/ missing)")
        return 0

    if not tests_dir.exists():
        print(f"⚠️  tests dir not found: {tests_dir.relative_to(REPO_ROOT)}")
        print("    (stage 04 not yet started)")
        return 0

    schemas = extract_schemas(schemas_dir)
    test_content = extract_test_references(tests_dir)

    missing_models = []
    for model in sorted(schemas["models"]):
        if model not in test_content:
            missing_models.append(model)

    missing_errors = []
    for class_name, consts in schemas["errors"].items():
        for const in consts:
            # Look for either the const name or its common string pattern
            if const not in test_content:
                missing_errors.append(f"{class_name}.{const}")

    total_models = len(schemas["models"])
    total_errors = sum(len(v) for v in schemas["errors"].values())

    print(f"\n📋 Schema coverage for {project}")
    print(f"   Models: {total_models - len(missing_models)}/{total_models} covered")
    print(f"   Errors: {total_errors - len(missing_errors)}/{total_errors} covered")

    if missing_models:
        print(f"\n❌ Models not referenced in tests:")
        for m in missing_models:
            print(f"   - {m}")

    if missing_errors:
        print(f"\n❌ Error codes not referenced in tests:")
        for e in missing_errors:
            print(f"   - {e}")

    if missing_models or missing_errors:
        return 1

    print(f"\n✅ All schema items covered")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    return check_coverage(sys.argv[1])


if __name__ == "__main__":
    sys.exit(main())
