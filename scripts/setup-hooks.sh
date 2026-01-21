#!/bin/bash
# Setup Git hooks for Tailpaste

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
GIT_HOOKS_DIR="${PROJECT_ROOT}/.git/hooks"

echo "🔧 Setting up Git hooks for Tailpaste"
echo "======================================"

# Check if .git directory exists
if [ ! -d "${PROJECT_ROOT}/.git" ]; then
    echo "❌ Not a git repository"
    exit 1
fi

# Create hooks directory if it doesn't exist
mkdir -p "$GIT_HOOKS_DIR"

# Install pre-commit hook
echo "📝 Installing pre-commit hook..."
cat > "${GIT_HOOKS_DIR}/pre-commit" << 'EOF'
#!/bin/bash
# Pre-commit hook for Tailpaste

SCRIPT_DIR="$(git rev-parse --show-toplevel)/scripts"
HOOK_SCRIPT="${SCRIPT_DIR}/pre-commit-hook.py"

if [ -f "$HOOK_SCRIPT" ]; then
    python3 "$HOOK_SCRIPT"
    exit $?
else
    echo "⚠️  Pre-commit hook script not found: $HOOK_SCRIPT"
    echo "Skipping pre-commit checks..."
    exit 0
fi
EOF

chmod +x "${GIT_HOOKS_DIR}/pre-commit"
echo "✅ Pre-commit hook installed"

# Install commit-msg hook (for commit message validation)
echo "📝 Installing commit-msg hook..."
cat > "${GIT_HOOKS_DIR}/commit-msg" << 'EOF'
#!/bin/bash
# Commit message validation hook

COMMIT_MSG_FILE=$1
COMMIT_MSG=$(cat "$COMMIT_MSG_FILE")

# Check minimum length
if [ ${#COMMIT_MSG} -lt 10 ]; then
    echo "❌ Commit message too short (minimum 10 characters)"
    echo "Please provide a more descriptive commit message"
    exit 1
fi

# Check for conventional commits format (optional)
# Uncomment to enforce conventional commits
# if ! echo "$COMMIT_MSG" | grep -qE '^(feat|fix|docs|style|refactor|test|chore|perf)(\(.+\))?: .+'; then
#     echo "⚠️  Consider using conventional commits format:"
#     echo "   feat: add new feature"
#     echo "   fix: fix a bug"
#     echo "   docs: update documentation"
#     echo "   style: formatting changes"
#     echo "   refactor: code refactoring"
#     echo "   test: add or update tests"
#     echo "   chore: maintenance tasks"
#     echo "   perf: performance improvements"
# fi

exit 0
EOF

chmod +x "${GIT_HOOKS_DIR}/commit-msg"
echo "✅ Commit-msg hook installed"

# Install pre-push hook (for running tests before push)
echo "📝 Installing pre-push hook..."
cat > "${GIT_HOOKS_DIR}/pre-push" << 'EOF'
#!/bin/bash
# Pre-push hook for Tailpaste

echo "🧪 Running tests before push..."

cd "$(git rev-parse --show-toplevel)"

# Run quick test suite
if pytest tests/ -v --tb=short; then
    echo "✅ Tests passed, proceeding with push"
    exit 0
else
    echo "❌ Tests failed, push aborted"
    echo "Fix the failing tests before pushing"
    exit 1
fi
EOF

chmod +x "${GIT_HOOKS_DIR}/pre-push"
echo "✅ Pre-push hook installed"

echo ""
echo "======================================"
echo "✅ Git hooks installed successfully!"
echo "======================================"
echo ""
echo "Installed hooks:"
echo "  • pre-commit: Code quality checks"
echo "  • commit-msg: Commit message validation"
echo "  • pre-push: Test suite validation"
echo ""
echo "To skip hooks temporarily, use:"
echo "  git commit --no-verify"
echo "  git push --no-verify"
echo ""
