#!/usr/bin/env bash
# unlock_tests.sh — 解锁测试目录，必须提供理由，留下审计记录
#
# Usage:
#   scripts/unlock_tests.sh <tests-dir> "<reason>"
#   scripts/unlock_tests.sh hermes/stages/04-development/tests "接口变更：FetchDaily 增加 adjust 参数"
#
# 解锁只应在接口变更流程中使用：
#   1. 修改 stages/03-module-design/schemas/
#   2. 解锁
#   3. 删除老测试文件
#   4. 重新生成新测试
#   5. 重新锁定

set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 <tests-dir> \"<reason>\"" >&2
  echo "" >&2
  echo "Reason is REQUIRED. Unlocking leaves an audit trail." >&2
  exit 2
fi

TESTS_DIR="$1"
REASON="$2"

if [ ! -d "$TESTS_DIR" ]; then
  echo "ERROR: directory not found: $TESTS_DIR" >&2
  exit 1
fi

if [ ${#REASON} -lt 10 ]; then
  echo "ERROR: reason must be at least 10 characters" >&2
  exit 1
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
LOCK_DIR="$REPO_ROOT/.git/locks"
AUDIT_FILE="$LOCK_DIR/unlock-audit.log"
mkdir -p "$LOCK_DIR"

# 检测操作系统，使用对应的解锁方式
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*|Windows_NT)
    # Windows: 使用 attrib 移除只读属性
    find "$TESTS_DIR" -type f -exec attrib -R {} \; 2>/dev/null || \
    find "$TESTS_DIR" -type f | while read -r f; do
      attrib -R "$(cygpath -w "$f" 2>/dev/null || echo "$f")" 2>/dev/null || true
    done
    ;;
  *)
    # Unix: 使用 chmod
    find "$TESTS_DIR" -type f -exec chmod 644 {} \;
    find "$TESTS_DIR" -type d -exec chmod 755 {} \;
    ;;
esac

# 删除锁标记
LOCK_ID=$(echo "$TESTS_DIR" | tr '/' '-')
LOCK_FILE="$LOCK_DIR/$LOCK_ID.lock"
rm -f "$LOCK_FILE"

# 审计记录
{
  echo "---"
  echo "unlocked_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "unlocked_by: $(whoami)@$(hostname)"
  echo "tests_dir: $TESTS_DIR"
  echo "reason: $REASON"
} >> "$AUDIT_FILE"

echo "🔓 Unlocked $TESTS_DIR"
echo "   Audit entry appended to $AUDIT_FILE"
echo ""
echo "⚠️  Remember to re-lock after interface changes are complete:"
echo "   scripts/lock_tests.sh $TESTS_DIR"
