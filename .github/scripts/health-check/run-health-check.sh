#!/bin/bash
# Run health check for Tailpaste service
# Arguments: None
# Environment: TAILPASTE_URL must be set

set -euo pipefail

echo "🏥 Running health check..."
echo "🛠️ Checking environment variables..."
echo "TAILPASTE_URL: $TAILPASTE_URL"

# Run the health check script
python3 scripts/health/health_check.py --export /tmp/health_check_results.json

# Store the exit code
HEALTH_STATUS=$?

if [ $HEALTH_STATUS -eq 0 ]; then
  echo "✅ Health check passed"
else
  echo "❌ Health check failed"
fi

exit $HEALTH_STATUS
