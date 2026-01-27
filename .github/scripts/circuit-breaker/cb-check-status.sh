#!/bin/bash
# Check circuit breaker status and output results
# Arguments: $1 - GitHub repository
# Environment: GH_TOKEN must be set

set -euo pipefail

REPOSITORY=$1

echo "🔍 Checking comprehensive circuit breaker status..."

# Use the enhanced circuit breaker script
python3 scripts/ci/circuit_breaker.py --repo "$REPOSITORY" status --json > /tmp/cb_status.json

# Parse status
CB_STATUS=$(python3 -c "import json; data=json.load(open('/tmp/cb_status.json')); print(data['status'])")
RECOVERY_FAILURES=$(python3 -c "import json; data=json.load(open('/tmp/cb_status.json')); print(data['recovery_failure_count'])")
DEPLOYMENT_FAILURES=$(python3 -c "import json; data=json.load(open('/tmp/cb_status.json')); print(data['deployment_failure_count'])")
RECOVERY_THRESHOLD=$(python3 -c "import json; data=json.load(open('/tmp/cb_status.json')); print(data['recovery_threshold'])")
DEPLOYMENT_THRESHOLD=$(python3 -c "import json; data=json.load(open('/tmp/cb_status.json')); print(data['deployment_threshold'])")

echo "Circuit Breaker Status: $CB_STATUS"
echo "Recovery Failures: $RECOVERY_FAILURES / $RECOVERY_THRESHOLD"
echo "Deployment Failures: $DEPLOYMENT_FAILURES / $DEPLOYMENT_THRESHOLD"

# Output for GitHub Actions
echo "CB_STATUS=$CB_STATUS"
echo "RECOVERY_FAILURES=$RECOVERY_FAILURES"
echo "DEPLOYMENT_FAILURES=$DEPLOYMENT_FAILURES"
echo "RECOVERY_THRESHOLD=$RECOVERY_THRESHOLD"
echo "DEPLOYMENT_THRESHOLD=$DEPLOYMENT_THRESHOLD"

# Check if thresholds are exceeded
RECOVERY_EXCEEDED=$([[ $RECOVERY_FAILURES -ge $RECOVERY_THRESHOLD ]] && echo "true" || echo "false")
DEPLOYMENT_EXCEEDED=$([[ $DEPLOYMENT_FAILURES -ge $DEPLOYMENT_THRESHOLD ]] && echo "true" || echo "false")

echo "RECOVERY_EXCEEDED=$RECOVERY_EXCEEDED"
echo "DEPLOYMENT_EXCEEDED=$DEPLOYMENT_EXCEEDED"

if [ "$CB_STATUS" = "open" ]; then
  echo "🚫 Circuit breaker is currently OPEN"
elif [ "$RECOVERY_EXCEEDED" = "true" ] || [ "$DEPLOYMENT_EXCEEDED" = "true" ]; then
  echo "⚠️  Thresholds exceeded but circuit breaker is still closed"
else
  echo "✅ Circuit breaker is healthy"
fi
