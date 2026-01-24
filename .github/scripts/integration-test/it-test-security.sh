#!/bin/bash
# Test security and concurrent requests

set -euo pipefail

echo "⚡ Testing concurrent requests..."
for i in $(seq 1 10); do
  (curl -s -X POST -H "Content-Type: text/plain" -d "Concurrent test $i" http://tailpaste:8080/ > /dev/null) &
done
wait
echo "✓ Concurrent requests completed"

echo "🔒 Testing proxy header rejection..."
HEADERS=("X-Forwarded-For: 1.2.3.4" "X-Real-IP: 1.2.3.4" "X-Forwarded-Proto: https")

for HEADER in "${HEADERS[@]}"; do
  HTTP_CODE=$(curl -s -w "%{http_code}" -o /dev/null -X POST -H "Content-Type: text/plain" -H "$HEADER" -d "Should be rejected" https://paste.bytes.coffee/)
  
  if [ "$HTTP_CODE" = "403" ]; then
    echo "✓ Correctly rejected request with: $HEADER"
  else
    echo "❌ Expected 403, got $HTTP_CODE for: $HEADER"
    exit 1
  fi
done
