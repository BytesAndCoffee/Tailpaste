#!/usr/bin/env bash
set -euo pipefail

echo "🧹 Cleaning up Tailpaste project..."

# Remove Python cache files
echo "  Removing Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true

# Remove .DS_Store files
echo "  Removing .DS_Store files..."
find . -name ".DS_Store" -delete 2>/dev/null || true

# Remove pytest cache
echo "  Removing pytest cache..."
rm -rf .pytest_cache 2>/dev/null || true

# Remove mypy cache
echo "  Removing mypy cache..."
rm -rf .mypy_cache 2>/dev/null || true

# Remove coverage files (keeping coverage.xml for CI)
echo "  Removing coverage artifacts..."
rm -rf htmlcov 2>/dev/null || true
rm -f .coverage 2>/dev/null || true

# Remove hypothesis cache
echo "  Removing hypothesis cache..."
rm -rf .hypothesis 2>/dev/null || true

# Clean up old log files (if any)
if [ -d "logs" ]; then
    echo "  Cleaning old log files..."
    find logs -name "*.log" -mtime +7 -delete 2>/dev/null || true
fi

# Clean up tmp files
echo "  Removing temporary files..."
rm -f /tmp/health_result_* 2>/dev/null || true
rm -f /tmp/orchestration_report.json 2>/dev/null || true

echo "✅ Cleanup complete!"
