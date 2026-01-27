#!/bin/sh
# Docker entrypoint script for tailpaste
# Starts Tailscale daemon and connects to tailnet before starting the application

set -e

echo "Starting Tailscale daemon..."

# Create necessary directories
mkdir -p /var/lib/tailscale /var/run/tailscale /config

# Start tailscaled in the background with LocalAPI enabled (kernel networking)
/usr/local/bin/tailscaled \
    --state=/var/lib/tailscale/tailscaled.state \
    --socket=/var/run/tailscale/tailscaled.sock \
    --statedir=/var/lib/tailscale &
TAILSCALED_PID=$!

# Wait for tailscaled to be ready
echo "Waiting for Tailscale daemon to be ready..."
sleep 5

# Authenticate with Tailscale using ephemeral auth key
if [ -n "$TAILSCALE_AUTHKEY" ]; then
    echo "Authenticating with Tailscale..."
    /usr/local/bin/tailscale up \
        --authkey="$TAILSCALE_AUTHKEY" \
        --hostname="${TAILSCALE_HOSTNAME:-tailpaste}" \
        --accept-routes=false \
        --accept-dns=true \
        --ssh
    
    # Wait for connection to be fully established
    echo "Waiting for Tailscale connection..."
    sleep 3
    
    # Verify connection
    /usr/local/bin/tailscale status
    
    # Explicitly disable any serve configuration
    echo "Disabling Tailscale serve..."
    /usr/local/bin/tailscale serve reset || true
    
    echo "Tailscale connected successfully"
else
    echo "ERROR: TAILSCALE_AUTHKEY environment variable is required"
    exit 1
fi

# Ensure data directory has proper permissions
# The volume mount may have restrictive permissions from the host
mkdir -p /data
chmod 777 /data  # Allow write access for database creation
touch /data/.test && rm /data/.test || {
    echo "ERROR: Cannot write to /data directory"
    exit 1
}

echo "Starting tailpaste..."

# Create log directory for diagnostics
mkdir -p /var/log/tailpaste

# Function to start the app with enhanced monitoring
start_app() {
    APP_LOG="/var/log/tailpaste/app-$(date +%s).log"
    
    # Start app and capture PID, stderr, stdout
    python /app/main.py > "$APP_LOG" 2>&1 &
    APP_PID=$!
    
    echo "App started with PID: $APP_PID"
    echo "App logging to: $APP_LOG"
    
    # Also log to stdout for Docker logs
    (tail -f "$APP_LOG" 2>/dev/null &)
}

# Function to check process exit status
check_app_exit() {
    local pid=$1
    if wait $pid 2>/dev/null; then
        EXIT_CODE=$?
    else
        EXIT_CODE=$?
    fi
    echo "$EXIT_CODE"
}

# Start the app initially
start_app

# Wait for the app to be ready
sleep 2

echo ""
echo "✓ tailpaste is running!"
echo "✓ Service is accessible on your tailnet at: http://100.112.76.12:8080"
echo "  (Direct tailnet access - no serve proxy)"
echo ""
echo "✓ SSH access enabled via Tailscale SSH"
echo "  SSH as 'inspector' user: tailscale ssh inspector@<tailnet-hostname>"
echo "  User has sudo access for service inspection"
echo ""
echo "📋 Diagnostic logs saved to: /var/log/tailpaste/"
echo ""

# Monitor and restart app if it crashes
CRASH_COUNT=0
CRASH_WINDOW_START=$(date +%s)

while true; do
    if ! kill -0 $APP_PID 2>/dev/null; then
        CURRENT_TIME=$(date '+%Y-%m-%d %H:%M:%S')
        EXIT_CODE=$(check_app_exit $APP_PID)
        
        # Log crash details
        echo "🚨 ========================================" >&2
        echo "🚨 CRASH DETECTED at $CURRENT_TIME" >&2
        echo "🚨 Process PID: $APP_PID" >&2
        echo "🚨 Exit Code: $EXIT_CODE" >&2
        echo "🚨 ========================================" >&2
        
        # Interpret exit codes
        case $EXIT_CODE in
            0)
                echo "❌ App exited cleanly (code 0) - check logs for shutdown reason" >&2
                ;;
            1)
                echo "❌ Generic error (code 1)" >&2
                ;;
            127)
                echo "❌ Command not found (code 127) - binary issue" >&2
                ;;
            137)
                echo "❌ SIGKILL received (code 137) - likely OOMKill or external termination" >&2
                ;;
            143)
                echo "❌ SIGTERM received (code 143) - graceful termination signal" >&2
                ;;
            *)
                echo "❌ Exit code: $EXIT_CODE" >&2
                ;;
        esac
        
        # Check for resource issues
        echo "📊 System diagnostics:" >&2
        free -h 2>/dev/null | tail -1 >&2 || echo "  (memory info unavailable)" >&2
        df -h /data 2>/dev/null | tail -1 >&2 || echo "  (disk info unavailable)" >&2
        
        # Check last log lines
        if [ -f "/var/log/tailpaste/app-"* ]; then
            echo "📝 Last 20 lines from app log:" >&2
            tail -20 /var/log/tailpaste/app-* 2>/dev/null | head -20 >&2 || echo "  (no logs available)" >&2
        fi
        
        # Track crash frequency
        CURRENT_WINDOW=$(date +%s)
        if [ $((CURRENT_WINDOW - CRASH_WINDOW_START)) -gt 300 ]; then
            CRASH_COUNT=0
            CRASH_WINDOW_START=$CURRENT_WINDOW
        fi
        CRASH_COUNT=$((CRASH_COUNT + 1))
        
        if [ $CRASH_COUNT -gt 5 ]; then
            echo "🛑 App crashed 5+ times in 5 minutes - stopping restart loop" >&2
            echo "   Check logs in: /var/log/tailpaste/" >&2
            exit 1
        fi
        
        echo "⏳ Restarting app in 5 seconds (attempt $CRASH_COUNT)..."
        sleep 5
        start_app
    fi
    
    # Check tailscaled is still running
    if ! kill -0 $TAILSCALED_PID 2>/dev/null; then
        echo "🚨 ERROR: Tailscaled died at $(date)"
        echo "Container must restart to recover Tailscale"
        exit 1
    fi
    
    sleep 10
done
