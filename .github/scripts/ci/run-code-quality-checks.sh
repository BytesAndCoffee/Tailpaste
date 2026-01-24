#!/bin/bash
# Run code quality checks with conditional execution

set -e

QUALITY_CHECKS_FAILED=0

# Conditional execution based on configuration
if [ "$ENABLE_FLAKE8" = "true" ]; then
  echo "🔍 Running linting..."
  flake8 src/ tests/ --max-line-length=120 --exclude=venv --statistics --output-file=flake8-report.txt
  FLAKE8_EXIT_CODE=$?
  if [ $FLAKE8_EXIT_CODE -ne 0 ]; then
    echo "❌ Flake8 linting failed"
    QUALITY_CHECKS_FAILED=1
  else
    echo "✅ Flake8 linting passed"
  fi
else
  echo "⏭️ Flake8 linting disabled"
fi

if [ "$ENABLE_BLACK" = "true" ]; then
  echo "🎨 Checking code formatting..."
  black --check src/ tests/ --diff
  BLACK_EXIT_CODE=$?
  if [ $BLACK_EXIT_CODE -ne 0 ]; then
    echo "❌ Black formatting check failed"
    QUALITY_CHECKS_FAILED=1
  else
    echo "✅ Black formatting check passed"
  fi
else
  echo "⏭️ Black formatting check disabled"
fi

if [ "$ENABLE_MYPY" = "true" ]; then
  echo "🔍 Type checking..."
  mypy src/ --ignore-missing-imports --junit-xml=mypy-report.xml
  MYPY_EXIT_CODE=$?
  if [ $MYPY_EXIT_CODE -ne 0 ]; then
    echo "❌ MyPy type checking failed"
    QUALITY_CHECKS_FAILED=1
  else
    echo "✅ MyPy type checking passed"
  fi
else
  echo "⏭️ MyPy type checking disabled"
fi

if [ "$ENABLE_BANDIT" = "true" ]; then
  echo "🔒 Security scanning..."
  bandit -r src/ -ll -f json -o bandit-report.json
  BANDIT_EXIT_CODE=$?
  if [ $BANDIT_EXIT_CODE -ne 0 ]; then
    echo "❌ Bandit security scan failed"
    QUALITY_CHECKS_FAILED=1
  else
    echo "✅ Bandit security scan passed"
  fi
else
  echo "⏭️ Bandit security scanning disabled"
fi

# CI Gating: Fail if any enabled quality check fails
if [ $QUALITY_CHECKS_FAILED -eq 1 ]; then
  echo "❌ One or more code quality checks failed. Blocking artifact creation."
  exit 1
fi

echo "✅ All enabled code quality checks passed"
