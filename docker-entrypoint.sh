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

# Function to start the app
start_app() {
    python /app/main.py &
    APP_PID=$!
    echo "App started with PID: $APP_PID"
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

# Monitor and restart app if it crashes
while true; do
    if ! kill -0 $APP_PID 2>/dev/null; then
        echo "ERROR: App process $APP_PID died at $(date)"
        echo "Restarting app in 5 seconds..."
        sleep 5
        start_app
    fi
    
    # Check tailscaled is still running
    if ! kill -0 $TAILSCALED_PID 2>/dev/null; then
        echo "ERROR: Tailscaled died at $(date)"
        echo "Container must restart to recover Tailscale"
        exit 1
    fi
    
    sleep 10
done
