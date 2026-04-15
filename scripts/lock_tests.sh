#!/usr/bin/env bash
# lock_tests.sh — 用文件权限保护测试目录，防止任何进程（包括 AI 模型）修改
#
# Usage:
#   scripts/lock_tests.sh <tests-dir>
#   scripts/lock_tests.sh hermes/stages/04-development/tests
#
# 效果：
#   - Linux/macOS: chmod 444（文件）/ 555（目录）
#   - Windows/MSYS2: attrib +R（只读属性）
#   - 任何 Edit/Write 会得到 Permission denied
#
# 要解锁，使用 unlock_tests.sh（需要显式解锁，留下审计痕迹）

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <tests-dir>" >&2
  exit 2
fi

TESTS_DIR="$1"

if [ ! -d "$TESTS_DIR" ]; then
  echo "ERROR: directory not found: $TESTS_DIR" >&2
  exit 1
fi

# 找到仓库根目录，记录锁状态
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
LOCK_DIR="$REPO_ROOT/.git/locks"
mkdir -p "$LOCK_DIR"

# 检测操作系统，使用对应的锁定方式
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*|Windows_NT)
    # Windows: 使用 attrib 设置只读属性
    find "$TESTS_DIR" -type f -exec attrib +R {} \; 2>/dev/null || \
    find "$TESTS_DIR" -type f | while read -r f; do
      attrib +R "$(cygpath -w "$f" 2>/dev/null || echo "$f")" 2>/dev/null || true
    done
    ;;
  *)
    # Unix: 使用 chmod
    find "$TESTS_DIR" -type f -exec chmod 444 {} \;
    find "$TESTS_DIR" -type d -exec chmod 555 {} \;
    ;;
esac

# 记录锁标记（包含时间戳和目录路径）
LOCK_ID=$(echo "$TESTS_DIR" | tr '/' '-')
LOCK_FILE="$LOCK_DIR/$LOCK_ID.lock"
{
  echo "locked_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "tests_dir=$TESTS_DIR"
  echo "locked_by=$(whoami)@$(hostname)"
} > "$LOCK_FILE"

echo "🔒 Locked $TESTS_DIR"
echo "   Files: $(find "$TESTS_DIR" -type f | wc -l)"
echo "   Lock marker: $LOCK_FILE"
echo ""
echo "To unlock (requires justification), run:"
echo "   scripts/unlock_tests.sh $TESTS_DIR \"<reason>\""
