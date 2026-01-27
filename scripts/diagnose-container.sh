#!/bin/bash
# Diagnostic script to investigate why the tailpaste container is dying

set -e

CONTAINER_NAME="tailpaste"

echo "🔍 === Tailpaste Container Diagnostics ==="
echo ""

# Check if container exists
if ! docker ps -a --filter name=$CONTAINER_NAME --format '{{.Names}}' | grep -q $CONTAINER_NAME; then
    echo "❌ Container '$CONTAINER_NAME' not found"
    exit 1
fi

# Container status
echo "1️⃣  Container Status:"
docker ps -a --filter name=$CONTAINER_NAME --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
echo ""

# Exit code and state details
echo "2️⃣  Detailed State:"
STATE=$(docker inspect $CONTAINER_NAME --format='{{json .State}}' | python3 -m json.tool)
echo "$STATE"
echo ""

# Check if it was OOMKilled
OOMKILLED=$(docker inspect $CONTAINER_NAME --format='{{.State.OOMKilled}}')
if [ "$OOMKILLED" = "true" ]; then
    echo "⚠️  WARNING: Container was killed due to OUT OF MEMORY!"
    echo "   Current memory limits:"
    docker inspect $CONTAINER_NAME --format='{{json .HostConfig.Memory}}' 2>/dev/null || echo "   No memory limit set"
    echo ""
fi

# Recent logs (last 50 lines)
echo "3️⃣  Recent Docker Logs (last 50 lines):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker logs --tail 50 $CONTAINER_NAME 2>&1 || echo "(No logs available)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check volume diagnostics
echo "4️⃣  Volume & Storage:"
docker inspect $CONTAINER_NAME --format='{{range .Mounts}}Mount: {{.Source}} -> {{.Destination}} ({{.Mode}})
{{end}}'
echo ""

# Check for crash logs inside container
echo "5️⃣  Crash Logs (if available):"
if docker exec $CONTAINER_NAME ls -la /var/log/tailpaste/ 2>/dev/null; then
    echo "Recent crash logs:"
    docker exec $CONTAINER_NAME tail -100 /var/log/tailpaste/app-* 2>/dev/null | tail -50 || echo "No crash logs"
else
    echo "  No /var/log/tailpaste directory found"
fi
echo ""

# Resource usage when running
if docker ps --filter name=$CONTAINER_NAME | grep -q $CONTAINER_NAME; then
    echo "6️⃣  Current Resource Usage:"
    docker stats $CONTAINER_NAME --no-stream --format 'table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}'
else
    echo "6️⃣  Container is not running (cannot get resource usage)"
fi
echo ""

# Network info
echo "7️⃣  Network Status:"
docker inspect $CONTAINER_NAME --format='{{range .NetworkSettings.Networks}}Network: {{.}}
{{end}}' || echo "Unable to get network info"
echo ""

# Restart policy
echo "8️⃣  Restart Policy:"
docker inspect $CONTAINER_NAME --format='{{.HostConfig.RestartPolicy}}'
echo ""

echo "💡 Recommendations:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "• Check logs in ./logs/ directory (mounted from container)"
echo "• Look for 'Exit Code' above - see exit codes reference below"
echo "• If OOMKilled=true, increase memory limits in docker-compose.yml"
echo "• Run: docker logs -f $CONTAINER_NAME  (to watch logs live)"
echo "• SSH into container: docker exec -it $CONTAINER_NAME /bin/sh"
echo ""

echo "Exit Code Reference:"
echo "  0   = Clean exit (check logs for why)"
echo "  1   = Generic error (check logs)"
echo "  127 = Command not found"
echo "  137 = SIGKILL (OOMKill or external termination)"
echo "  143 = SIGTERM (graceful termination)"
echo "  139 = SIGSEGV (segmentation fault)"
