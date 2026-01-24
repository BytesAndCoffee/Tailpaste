#!/bin/bash
# Enhanced deployment verification script
# This script runs comprehensive deployment verification checks on the remote host

set -e

echo "=== CONTAINER STATUS VERIFICATION ==="

# Enhanced container running check
CONTAINER_NAME="tailpaste"
if ! docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -q "$CONTAINER_NAME"; then
  echo "❌ Container '$CONTAINER_NAME' is not running!"
  echo "Available containers:"
  docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
  echo "Recent container logs:"
  docker logs "$CONTAINER_NAME" --tail=50 2>/dev/null || echo "No logs available"
  exit 1
fi
echo "✓ Container '$CONTAINER_NAME' is running"

# Enhanced container health check
CONTAINER_STATUS=$(docker inspect --format='{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "unknown")
CONTAINER_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "none")
RESTART_COUNT=$(docker inspect --format='{{.RestartCount}}' "$CONTAINER_NAME" 2>/dev/null || echo "0")

echo "Container Status: $CONTAINER_STATUS"
echo "Container Health: $CONTAINER_HEALTH"  
echo "Restart Count: $RESTART_COUNT"

if [ "$CONTAINER_STATUS" != "running" ]; then
  echo "❌ Container is not in running state: $CONTAINER_STATUS"
  exit 1
fi

if [ "$RESTART_COUNT" -gt "0" ]; then
  echo "⚠️  Container has restarted $RESTART_COUNT times"
fi

echo "=== RESOURCE UTILIZATION CHECK ==="

# Check container resource usage
CONTAINER_STATS=$(docker stats "$CONTAINER_NAME" --no-stream --format "table {{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}")
echo "Container Resource Usage:"
echo "$CONTAINER_STATS"

# Check image information
IMAGE_INFO=$(docker inspect "$CONTAINER_NAME" --format='{{.Config.Image}}')
IMAGE_SIZE=$(docker images "$IMAGE_INFO" --format "{{.Size}}" | head -n 1)
echo "Image: $IMAGE_INFO"
echo "Image Size: $IMAGE_SIZE"

echo "=== NETWORK CONNECTIVITY CHECK ==="

# Enhanced Tailscale connectivity check
TAILSCALE_IP=$(docker exec "$CONTAINER_NAME" tailscale ip -4 2>/dev/null || echo "N/A")
TAILSCALE_STATUS=$(docker exec "$CONTAINER_NAME" tailscale status --json 2>/dev/null | jq -r '.BackendState' 2>/dev/null || echo "unknown")

echo "Tailscale IP: $TAILSCALE_IP"
echo "Tailscale Status: $TAILSCALE_STATUS"

if [ "$TAILSCALE_IP" = "N/A" ] || [ "$TAILSCALE_STATUS" != "Running" ]; then
  echo "⚠️  Tailscale connectivity issues detected"
else
  echo "✓ Tailscale connectivity verified"
fi

# Check port binding
PORT_BINDING=$(docker port "$CONTAINER_NAME" 8080 2>/dev/null || echo "none")
echo "Port 8080 binding: $PORT_BINDING"

echo "=== APPLICATION LOG ANALYSIS ==="

# Enhanced log analysis
RECENT_LOGS=$(docker logs "$CONTAINER_NAME" --tail=100 --since=5m 2>&1)

# Count different types of log entries
ERROR_COUNT=$(echo "$RECENT_LOGS" | grep -i "error" | grep -v "ERROR_LOG" | wc -l || echo 0)
WARNING_COUNT=$(echo "$RECENT_LOGS" | grep -i "warning\|warn" | wc -l || echo 0)
STARTUP_MESSAGES=$(echo "$RECENT_LOGS" | grep -i "starting\|started\|listening\|ready" | wc -l || echo 0)

echo "Recent log analysis (last 5 minutes):"
echo "- Errors: $ERROR_COUNT"
echo "- Warnings: $WARNING_COUNT"  
echo "- Startup messages: $STARTUP_MESSAGES"

if [ "$ERROR_COUNT" -gt "5" ]; then
  echo "❌ High error count detected ($ERROR_COUNT errors)"
  echo "Recent errors:"
  echo "$RECENT_LOGS" | grep -i "error" | grep -v "ERROR_LOG" | tail -5
  exit 1
elif [ "$ERROR_COUNT" -gt "0" ]; then
  echo "⚠️  Some errors detected ($ERROR_COUNT errors)"
  echo "Recent errors:"
  echo "$RECENT_LOGS" | grep -i "error" | grep -v "ERROR_LOG" | tail -3
else
  echo "✓ No significant errors in recent logs"
fi

echo "=== DEPLOYMENT SUMMARY ==="

# Write enhanced summary data
{
  echo "### Enhanced Deployment Verification Results"
  echo ""
  echo "#### Container Status"
  echo "- **Container Name**: $CONTAINER_NAME"
  echo "- **Status**: $CONTAINER_STATUS"
  echo "- **Health**: $CONTAINER_HEALTH"
  echo "- **Restart Count**: $RESTART_COUNT"
  echo "- **Image**: $IMAGE_INFO"
  echo "- **Image Size**: $IMAGE_SIZE"
  echo ""
  echo "#### Network Connectivity"
  echo "- **Tailscale IP**: $TAILSCALE_IP"
  echo "- **Tailscale Status**: $TAILSCALE_STATUS"
  echo "- **Port Binding**: $PORT_BINDING"
  echo ""
  echo "#### Application Health"
  echo "- **Recent Errors**: $ERROR_COUNT"
  echo "- **Recent Warnings**: $WARNING_COUNT"
  echo "- **Startup Messages**: $STARTUP_MESSAGES"
  echo ""
  echo "#### Resource Usage"
  echo "$CONTAINER_STATS"
} > /tmp/deployment_summary.txt

echo "✅ Enhanced deployment verification completed successfully!"
