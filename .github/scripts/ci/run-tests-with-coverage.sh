#!/bin/bash
# Run tests with coverage enforcement

set -e

echo "🧪 Running tests..."
pytest --cov=src tests/ --cov-report=xml --cov-report=html --cov-report=term-missing --junit-xml=pytest-report.xml
PYTEST_EXIT_CODE=$?

if [ $PYTEST_EXIT_CODE -ne 0 ]; then
  echo "❌ Tests failed. Blocking artifact creation."
  exit 1
fi

# Conditional coverage enforcement
if [ "$ENABLE_COVERAGE" = "true" ]; then
  echo "📊 Enforcing coverage threshold..."
  coverage report --fail-under="$COVERAGE_THRESHOLD"
  COVERAGE_EXIT_CODE=$?
  
  if [ $COVERAGE_EXIT_CODE -ne 0 ]; then
    echo "❌ Coverage threshold (${COVERAGE_THRESHOLD}%) not met. Blocking artifact creation."
    exit 1
  fi
  
  echo "✅ Coverage threshold met"
else
  echo "⏭️ Coverage enforcement disabled"
fi

echo "✅ All tests passed and coverage requirements met"
