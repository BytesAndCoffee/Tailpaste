#!/bin/bash
# Execute comprehensive health checks
# Extracted from health-monitor.yml

set -e

echo "🔍 Executing comprehensive health checks using enhanced health check script..."

# Run the enhanced health check script with JSON output
if python3 scripts/health/health_check.py --json --export /tmp/health_results.json; then
  echo "✅ Health checks completed successfully"
  HEALTH_CHECK_SUCCESS=true
else
  echo "❌ Health checks failed"
  HEALTH_CHECK_SUCCESS=false
fi

# Parse results from the health check script
if [ -f "/tmp/health_results.json" ]; then
  OVERALL_HEALTH=$(python3 scripts/health/parse_health_results.py /tmp/health_results.json overall_status)
  HEALTH_DETAILS=$(python3 scripts/health/parse_health_results.py /tmp/health_results.json health_details)
  
  # Extract individual check results
  SERVICE_AVAILABLE=$(python3 scripts/health/parse_health_results.py /tmp/health_results.json service_available)
  FUNCTIONALITY_OK=$(python3 scripts/health/parse_health_results.py /tmp/health_results.json functionality_ok)
  CONTAINER_HEALTHY=$(python3 scripts/health/parse_health_results.py /tmp/health_results.json container_healthy)
  
  echo "Health check results:"
  echo "  Overall: $OVERALL_HEALTH"
  echo "  Service Available: $SERVICE_AVAILABLE"
  echo "  Functionality OK: $FUNCTIONALITY_OK"
  echo "  Container Healthy: $CONTAINER_HEALTHY"
else
  echo "⚠️  Health results file not found, using fallback status"
  OVERALL_HEALTH="unknown"
  HEALTH_DETAILS="Health check script did not produce results file"
  SERVICE_AVAILABLE="false"
  FUNCTIONALITY_OK="false"
  CONTAINER_HEALTHY="false"
fi

# Set outputs for next steps
echo "OVERALL_HEALTH=$OVERALL_HEALTH" >> "$GITHUB_OUTPUT"
echo "HEALTH_DETAILS=$HEALTH_DETAILS" >> "$GITHUB_OUTPUT"
echo "SERVICE_AVAILABLE=$SERVICE_AVAILABLE" >> "$GITHUB_OUTPUT"
echo "FUNCTIONALITY_OK=$FUNCTIONALITY_OK" >> "$GITHUB_OUTPUT"
echo "CONTAINER_HEALTHY=$CONTAINER_HEALTHY" >> "$GITHUB_OUTPUT"
echo "HEALTH_CHECK_SUCCESS=$HEALTH_CHECK_SUCCESS" >> "$GITHUB_OUTPUT"
