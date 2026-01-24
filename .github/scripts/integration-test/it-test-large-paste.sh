#!/bin/bash
# Test large paste handling

set -euo pipefail

echo "📦 Testing large paste (500KB)..."
dd if=/dev/urandom bs=1024 count=500 2>/dev/null | base64 > /tmp/large_test.txt

PASTE_URL=$(curl -s -X POST -H "Content-Type: text/plain" --data-binary @/tmp/large_test.txt http://tailpaste:8080/)

if [ -z "$PASTE_URL" ]; then
  echo "❌ Failed to create large paste"
  rm -f /tmp/large_test.txt
  exit 1
fi
echo "✓ Created large paste: $PASTE_URL"

curl -s -o /tmp/retrieved.txt "$PASTE_URL"
if [ -s /tmp/retrieved.txt ]; then
  ORIGINAL_SIZE=$(wc -c < /tmp/large_test.txt)
  RETRIEVED_SIZE=$(wc -c < /tmp/retrieved.txt)
  echo "✓ Retrieved paste (Original: $ORIGINAL_SIZE bytes, Retrieved: $RETRIEVED_SIZE bytes)"
else
  echo "❌ Failed to retrieve large paste"
  exit 1
fi

rm -f /tmp/large_test.txt /tmp/retrieved.txt
