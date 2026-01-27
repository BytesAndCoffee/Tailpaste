#!/bin/bash
# Export circuit breaker logs
# Arguments: $1 - GitHub repository
# Environment: GH_TOKEN must be set

set -euo pipefail

REPOSITORY=$1

echo "📋 Exporting circuit breaker logs and status..."

# Export comprehensive status
python3 scripts/ci/circuit_breaker.py --repo "$REPOSITORY" status --export /tmp/circuit_breaker_export.json

# Show event log
echo "📝 Recent Circuit Breaker Events:"
python3 scripts/ci/circuit_breaker.py --repo "$REPOSITORY" events

# Show recovery history
echo "🔄 Recovery History:"
python3 scripts/ci/circuit_breaker.py --repo "$REPOSITORY" history

# Upload export as artifact
echo "📤 Uploading circuit breaker export as artifact..."
