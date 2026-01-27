#!/bin/bash
# Real-time container monitoring script
# Watches for crashes and logs when they occur

CONTAINER_NAME="tailpaste"
MONITOR_LOG="./container-monitor.log"
LAST_STATE=""
LAST_PID=""

echo "🔍 Starting continuous container monitoring for $CONTAINER_NAME..."
echo "   Logging to: $MONITOR_LOG"
echo "   Press Ctrl+C to stop"
echo ""

# Function to log with timestamp
log_event() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $message" | tee -a "$MONITOR_LOG"
}

# Function to get current state
get_state() {
    docker inspect "$CONTAINER_NAME" --format='{{.State.Running}}:{{.State.ExitCode}}:{{.State.OOMKilled}}:{{.State.Error}}' 2>/dev/null || echo "not-found"
}

# Function to get process ID
get_app_pid() {
    docker top "$CONTAINER_NAME" 2>/dev/null | grep "python" | awk '{print $2}' | head -1 || echo ""
}

log_event "Monitor started"

while true; do
    CURRENT_STATE=$(get_state)
    
    if [ "$CURRENT_STATE" != "$LAST_STATE" ]; then
        IFS=':' read -r is_running exit_code oomkilled error <<< "$CURRENT_STATE"
        
        case "$is_running" in
            "true")
                if [ "$LAST_STATE" != "true:"* ]; then
                    log_event "✅ Container STARTED (running)"
                    PID=$(get_app_pid)
                    log_event "   App PID: $PID"
                    LAST_PID="$PID"
                fi
                ;;
            "false")
                log_event "❌ Container STOPPED"
                log_event "   Exit Code: $exit_code"
                [ "$oomkilled" = "true" ] && log_event "   ⚠️  OOMKilled: YES"
                [ -n "$error" ] && log_event "   Error: $error"
                
                # Get last logs
                log_event "📝 Last 10 log lines:"
                docker logs --tail 10 "$CONTAINER_NAME" 2>/dev/null | while IFS= read -r line; do
                    log_event "   │ $line"
                done
                ;;
            "not-found")
                log_event "⚠️  Container not found or Docker unreachable"
                ;;
        esac
        
        LAST_STATE="$CURRENT_STATE"
    else
        # Container is running - check if PID changed (indicates crash + restart)
        if [ "$CURRENT_STATE" = "true:"* ]; then
            CURRENT_PID=$(get_app_pid)
            if [ -n "$CURRENT_PID" ] && [ "$CURRENT_PID" != "$LAST_PID" ] && [ -n "$LAST_PID" ]; then
                log_event "🔄 App process restarted (PID changed: $LAST_PID → $CURRENT_PID)"
                LAST_PID="$CURRENT_PID"
            fi
        fi
    fi
    
    sleep 5
done
