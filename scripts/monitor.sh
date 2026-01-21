#!/bin/bash
# Monitoring script for Tailpaste
# Runs health checks and sends alerts if issues are detected

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="${PROJECT_ROOT}/logs"
HEALTH_CHECK_SCRIPT="${SCRIPT_DIR}/health_check.py"
LOG_ANALYZER_SCRIPT="${SCRIPT_DIR}/log_analyzer.py"

# Alert configuration (customize these)
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
EMAIL_ALERT="${EMAIL_ALERT:-}"
ALERT_ON_WARNING="${ALERT_ON_WARNING:-false}"

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Logging
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/monitor-$(date +%Y%m%d).log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $*${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $*${NC}" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] SUCCESS: $*${NC}" | tee -a "$LOG_FILE"
}

# Alert functions
send_slack_alert() {
    local message="$1"
    local severity="${2:-info}"
    
    if [ -z "$SLACK_WEBHOOK_URL" ]; then
        return
    fi
    
    local color="good"
    local icon=":white_check_mark:"
    
    case "$severity" in
        error)
            color="danger"
            icon=":x:"
            ;;
        warning)
            color="warning"
            icon=":warning:"
            ;;
    esac
    
    local payload=$(cat <<EOF
{
    "attachments": [{
        "color": "$color",
        "title": "$icon Tailpaste Alert",
        "text": "$message",
        "footer": "Tailpaste Monitoring",
        "ts": $(date +%s)
    }]
}
EOF
)
    
    curl -X POST -H 'Content-type: application/json' \
        --data "$payload" \
        "$SLACK_WEBHOOK_URL" \
        2>&1 | tee -a "$LOG_FILE"
}

send_email_alert() {
    local subject="$1"
    local body="$2"
    
    if [ -z "$EMAIL_ALERT" ] || ! command -v mail &> /dev/null; then
        return
    fi
    
    echo "$body" | mail -s "$subject" "$EMAIL_ALERT"
    log "Email alert sent to $EMAIL_ALERT"
}

# Main monitoring function
run_health_check() {
    log "Starting health check..."
    
    local health_report="${LOG_DIR}/health-$(date +%Y%m%d-%H%M%S).json"
    
    if python3 "$HEALTH_CHECK_SCRIPT" --export "$health_report"; then
        log_success "Health check passed"
        return 0
    else
        log_error "Health check failed"
        
        # Parse health report for details
        if [ -f "$health_report" ]; then
            local errors=$(jq -r '.errors[]' "$health_report" 2>/dev/null | tr '\n' ' ')
            local warnings=$(jq -r '.warnings[]' "$health_report" 2>/dev/null | tr '\n' ' ')
            
            if [ -n "$errors" ]; then
                log_error "Errors: $errors"
                send_slack_alert "Health check failed!\nErrors: $errors" "error"
                send_email_alert "Tailpaste Health Check Failed" "Errors detected:\n$errors"
            fi
            
            if [ -n "$warnings" ] && [ "$ALERT_ON_WARNING" = "true" ]; then
                log_warning "Warnings: $warnings"
                send_slack_alert "Health check warnings:\n$warnings" "warning"
            fi
        fi
        
        return 1
    fi
}

run_log_analysis() {
    log "Running log analysis..."
    
    local log_report="${LOG_DIR}/log-analysis-$(date +%Y%m%d-%H%M%S).json"
    
    if python3 "$LOG_ANALYZER_SCRIPT" --export "$log_report"; then
        log_success "Log analysis completed"
        
        # Check for critical error count
        if [ -f "$log_report" ]; then
            local error_count=$(jq -r '.metrics.error_count // 0' "$log_report")
            
            if [ "$error_count" -gt 10 ]; then
                log_warning "High error count detected: $error_count errors"
                send_slack_alert "High error count in logs: $error_count errors" "warning"
            fi
        fi
        
        return 0
    else
        log_error "Log analysis failed"
        return 1
    fi
}

check_disk_space() {
    log "Checking disk space..."
    
    local storage_path="${STORAGE_PATH:-./storage}"
    local threshold=90
    
    if [ -d "$storage_path" ]; then
        local usage=$(df -h "$storage_path" | tail -1 | awk '{print $5}' | sed 's/%//')
        
        if [ "$usage" -gt "$threshold" ]; then
            log_error "Disk usage critical: ${usage}%"
            send_slack_alert "Disk usage critical: ${usage}% (threshold: ${threshold}%)" "error"
            return 1
        else
            log "Disk usage: ${usage}%"
        fi
    fi
    
    return 0
}

check_docker_container() {
    log "Checking Docker container status..."
    
    if ! docker ps | grep -q tailpaste; then
        log_error "Tailpaste container is not running!"
        send_slack_alert "Tailpaste container is not running!" "error"
        send_email_alert "Tailpaste Container Down" "The Tailpaste container is not running. Please investigate."
        return 1
    fi
    
    log_success "Container is running"
    return 0
}

cleanup_old_logs() {
    log "Cleaning up old logs..."
    
    # Keep only last 30 days of logs
    find "$LOG_DIR" -name "*.log" -mtime +30 -delete
    find "$LOG_DIR" -name "*.json" -mtime +30 -delete
    
    log "Old logs cleaned up"
}

# Main execution
main() {
    log "========================================"
    log "Starting Tailpaste monitoring cycle"
    log "========================================"
    
    local exit_code=0
    
    # Run checks
    check_docker_container || exit_code=1
    run_health_check || exit_code=1
    run_log_analysis || exit_code=1
    check_disk_space || exit_code=1
    
    # Cleanup
    cleanup_old_logs
    
    if [ $exit_code -eq 0 ]; then
        log_success "All monitoring checks passed"
    else
        log_error "Some monitoring checks failed"
    fi
    
    log "========================================"
    log "Monitoring cycle completed"
    log "========================================"
    
    return $exit_code
}

# Run main function
main "$@"
