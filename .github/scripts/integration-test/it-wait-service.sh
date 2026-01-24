#!/bin/bash
# Wait for Tailpaste service to be available

set -euo pipefail

echo "⏳ Waiting for Tailpaste service to be reachable..."
for i in {1..90}; do
  if curl -f -s -o /dev/null http://tailpaste:8080/; then
    echo "Tailpaste is up"
    exit 0
  fi
  sleep 1
done
echo "Tailpaste failed to start"
exit 1
