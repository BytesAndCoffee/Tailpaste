#!/bin/bash
# Run basic integration tests

set -euo pipefail

echo "🔍 Testing service availability..."
if ! curl -f -s -o /dev/null http://tailpaste:8080/; then
  echo "❌ Service is not reachable"
  exit 1
fi
echo "✓ Service is reachable"

echo "📝 Testing paste creation and retrieval..."
TEST_CONTENT="Integration Test - $(date -u +%Y-%m-%dT%H:%M:%SZ)"
PASTE_URL=$(curl -s -X POST -H "Content-Type: text/plain" -d "$TEST_CONTENT" http://tailpaste:8080/)

if [ -z "$PASTE_URL" ]; then
  echo "❌ Failed to create paste"
  exit 1
fi
echo "✓ Created paste: $PASTE_URL"

RETRIEVED=$(curl -s "$PASTE_URL")
if [[ "$RETRIEVED" == *"$TEST_CONTENT"* ]]; then
  echo "✓ Paste content verified"
else
  echo "❌ Paste content mismatch"
  exit 1
fi
