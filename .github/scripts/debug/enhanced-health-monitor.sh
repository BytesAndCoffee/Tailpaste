#!/bin/bash
# Enhanced Health Monitoring with Debug Support
# Integrates comprehensive debugging into health check workflow

set -euo pipefail

# Import debug helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/debug/debug-helpers.sh"

export WORKFLOW_CONTEXT="Health-Monitor"

# ============================================================================
# Configuration
# ============================================================================

readonly SERVICE_URL="${TAILPASTE_URL:-http://tailpaste:8080}"
readonly HEALTH_CHECK_TIMEOUT=10
readonly MAX_RETRIES=3

# ============================================================================
# Health Check Implementation
# ============================================================================

check_service_availability() {
    log_info "Checking service availability..."
    
    local attempt=1
    while (( attempt <= MAX_RETRIES )); do
        log_debug "Attempt $attempt/$MAX_RETRIES: Testing $SERVICE_URL"
        
        if response=$(curl -s -m "$HEALTH_CHECK_TIMEOUT" -o /dev/null -w "%{http_code}" "$SERVICE_URL" 2>&1); then
            if [[ "$response" == "200" ]]; then
                log_info "✓ Service is available (HTTP $response)"
                return 0
            else
                log_warn "Service returned HTTP $response"
            fi
        else
            log_warn "Request failed: $response"
        fi
        
        ((attempt++))
        if (( attempt <= MAX_RETRIES )); then
            sleep 2
        fi
    done
    
    log_error "✗ Service unavailable after $MAX_RETRIES attempts"
    return 1
}

check_functionality() {
    log_info "Checking basic functionality..."
    
    local test_content="test-$(date +%s)"
    
    # Try to create a paste
    log_debug "Creating test paste..."
    create_response=$(curl -s -X POST "$SERVICE_URL" \
        -H "Content-Type: application/json" \
        -d "{\"content\": \"$test_content\"}" \
        -m "$HEALTH_CHECK_TIMEOUT" 2>&1) || {
        log_error "Failed to create test paste: $create_response"
        return 1
    }
    
    # Extract paste ID
    paste_id=$(echo "$create_response" | grep -oP '(?<="id":\s")[^"]+' | head -n1)
    
    if [[ -z "$paste_id" ]]; then
        log_error "Could not extract paste ID from response"
        log_debug "Response: $create_response"
        return 1
    fi
    
    log_debug "Created test paste with ID: $paste_id"
    
    # Try to retrieve the paste
    log_debug "Retrieving test paste..."
    retrieve_response=$(curl -s "$SERVICE_URL/$paste_id" \
        -m "$HEALTH_CHECK_TIMEOUT" 2>&1) || {
        log_error "Failed to retrieve test paste: $retrieve_response"
        return 1
    }
    
    if [[ "$retrieve_response" == *"$test_content"* ]]; then
        log_info "✓ Functionality check passed"
        return 0
    else
        log_error "Retrieved paste content doesn't match"
        log_debug "Expected: $test_content"
        log_debug "Got: $retrieve_response"
        return 1
    fi
}

check_tailscale_connectivity() {
    log_info "Checking Tailscale connectivity..."
    
    if ! command -v tailscale &> /dev/null; then
        log_warn "Tailscale CLI not available"
        return 1
    fi
    
    if tailscale status &> /dev/null; then
        local ip=$(tailscale ip -4 2>/dev/null || echo "unknown")
        log_info "✓ Tailscale connected (IP: $ip)"
        return 0
    else
        log_error "✗ Tailscale not connected"
        return 1
    fi
}

check_database() {
    log_info "Checking database status..."
    
    local db_path="${DATABASE_PATH:-./storage/tailpaste.db}"
    
    if [[ ! -f "$db_path" ]]; then
        log_warn "Database file not found at $db_path"
        return 1
    fi
    
    log_debug "Database file size: $(stat -f%z "$db_path" 2>/dev/null || stat -c%s "$db_path" 2>/dev/null || echo "unknown")"
    log_info "✓ Database exists"
    return 0
}

# ============================================================================
# Debug Output Generation
# ============================================================================

generate_health_debug_output() {
    local debug_file="${1:-/tmp/health-check-debug.log}"
    
    log_info "Generating health check debug output..."
    
    {
        echo "========== Health Check Debug Log =========="
        echo "Timestamp: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
        echo "Service URL: $SERVICE_URL"
        echo "Timeout: $HEALTH_CHECK_TIMEOUT seconds"
        echo "Max Retries: $MAX_RETRIES"
        echo ""
        
        echo "Environment:"
        env | grep -E "^(TAILPASTE|DATABASE|HEALTH)" | sort || echo "  (no matching variables)"
        echo ""
        
        echo "Network Status:"
        if command -v netstat &> /dev/null; then
            netstat -tuln | grep -E "(LISTEN|Active)" || true
        elif command -v ss &> /dev/null; then
            ss -tuln | grep -E "(LISTEN|State)" || true
        fi
        echo ""
        
        echo "DNS Resolution:"
        if [[ "$SERVICE_URL" =~ http://([^/:]+) ]]; then
            local host="${BASH_REMATCH[1]}"
            log_debug "Resolving host: $host"
            if command -v getent &> /dev/null; then
                getent hosts "$host" || echo "  Resolution failed"
            elif command -v nslookup &> /dev/null; then
                nslookup "$host" || echo "  Resolution failed"
            fi
        fi
        echo ""
        
    } | tee "$debug_file"
    
    log_info "Debug output saved to: $debug_file"
}

# ============================================================================
# Health Check Orchestration
# ============================================================================

run_health_checks() {
    local overall_status="healthy"
    local checks_passed=0
    local checks_failed=0
    
    log_info "=========================================="
    log_info "Starting Enhanced Health Check"
    log_info "=========================================="
    echo ""
    
    # Service availability
    if check_service_availability; then
        ((checks_passed++))
    else
        ((checks_failed++))
        overall_status="unhealthy"
    fi
    echo ""
    
    # Functionality
    if check_functionality; then
        ((checks_passed++))
    else
        ((checks_failed++))
        overall_status="unhealthy"
    fi
    echo ""
    
    # Tailscale connectivity
    if check_tailscale_connectivity; then
        ((checks_passed++))
    else
        ((checks_failed++))
        if [[ "$overall_status" == "healthy" ]]; then
            overall_status="degraded"
        fi
    fi
    echo ""
    
    # Database
    if check_database; then
        ((checks_passed++))
    else
        ((checks_failed++))
        if [[ "$overall_status" == "healthy" ]]; then
            overall_status="degraded"
        fi
    fi
    echo ""
    
    # Summary
    log_info "=========================================="
    log_info "Health Check Summary"
    log_info "=========================================="
    log_info "Checks Passed: $checks_passed"
    log_info "Checks Failed: $checks_failed"
    log_info "Overall Status: $overall_status"
    log_info "=========================================="
    
    # Output for GitHub Actions
    if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
        echo "OVERALL_HEALTH=$overall_status" >> "$GITHUB_OUTPUT"
        echo "CHECKS_PASSED=$checks_passed" >> "$GITHUB_OUTPUT"
        echo "CHECKS_FAILED=$checks_failed" >> "$GITHUB_OUTPUT"
        log_debug "Wrote health check results to GITHUB_OUTPUT"
    fi
    
    # Generate debug output
    generate_health_debug_output
    
    # Return appropriate exit code
    if [[ "$overall_status" == "healthy" ]]; then
        return 0
    else
        return 1
    fi
}

# ============================================================================
# Main Entry Point
# ============================================================================

main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --debug)
                DEBUG_LEVEL=$DEBUG_LEVEL_DEBUG
                log_info "Debug mode enabled"
                ;;
            --trace)
                enable_trace_mode
                ;;
            --diagnose)
                log_info "Running diagnostics before health checks..."
                run_full_diagnostics
                echo ""
                ;;
            --service-url)
                SERVICE_URL="$2"
                shift
                ;;
            *)
                log_warn "Unknown option: $1"
                ;;
        esac
        shift
    done
    
    run_health_checks
}

# Execute if not sourced
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi

