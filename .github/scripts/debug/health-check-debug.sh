#!/bin/bash
# Health Check with Enhanced Debugging Wrapper
# Automatically instruments and monitors health check execution

set -euo pipefail

# Import debug helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/debug/debug-helpers.sh"

# Default values
VERBOSE=false
DIAGNOSE=false
TRACE_EXECUTION=false
SAVE_ARTIFACTS=false
ARTIFACT_DIR="/tmp/health-check-artifacts"

# ============================================================================
# Argument Parsing
# ============================================================================

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -v|--verbose)
                VERBOSE=true
                DEBUG_LEVEL=$DEBUG_LEVEL_DEBUG
                ;;
            -vv|--very-verbose)
                VERBOSE=true
                DEBUG_LEVEL=$DEBUG_LEVEL_TRACE
                ;;
            -d|--diagnose)
                DIAGNOSE=true
                ;;
            -t|--trace)
                TRACE_EXECUTION=true
                ;;
            -s|--save-artifacts)
                SAVE_ARTIFACTS=true
                ARTIFACT_DIR="${2:-.}"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_warn "Unknown argument: $1"
                ;;
        esac
        shift
    done
}

show_help() {
    cat << 'EOF'
Health Check with Enhanced Debugging
Usage: health-check-debug.sh [OPTIONS]

OPTIONS:
  -v, --verbose           Enable verbose output (DEBUG level)
  -vv, --very-verbose     Enable very verbose output (TRACE level)
  -d, --diagnose          Run diagnostics before health checks
  -t, --trace             Enable execution tracing
  -s, --save-artifacts    Save debug artifacts to directory
  -h, --help              Show this help message

ENVIRONMENT VARIABLES:
  WORKFLOW_DEBUG_LEVEL    Override debug level (0-5)
  DEBUG_LOG_FILE          Custom debug log file path
  TAILPASTE_URL          Service URL to check (default: http://tailpaste:8080)

EXAMPLES:
  # Run with verbose output
  ./health-check-debug.sh -v
  
  # Run with diagnostics before checks
  ./health-check-debug.sh -d
  
  # Run with tracing and save artifacts
  ./health-check-debug.sh -t -s /tmp/artifacts

EOF
}

# ============================================================================
# Artifact Collection
# ============================================================================

initialize_artifacts() {
    if ! $SAVE_ARTIFACTS; then
        return 0
    fi
    
    log_info "Initializing artifact collection to: $ARTIFACT_DIR"
    mkdir -p "$ARTIFACT_DIR"
    
    # Create subdirectories
    mkdir -p "$ARTIFACT_DIR/logs"
    mkdir -p "$ARTIFACT_DIR/outputs"
    mkdir -p "$ARTIFACT_DIR/diagnostics"
    
    # Update debug log file path
    DEBUG_LOG_FILE="$ARTIFACT_DIR/logs/health-check.log"
    export DEBUG_LOG_FILE
    
    log_info "Artifact directories created"
}

collect_artifacts() {
    if ! $SAVE_ARTIFACTS; then
        return 0
    fi
    
    log_info "Collecting debug artifacts..."
    
    # Copy GitHub output files if they exist
    if [[ -n "${GITHUB_OUTPUT:-}" && -f "$GITHUB_OUTPUT" ]]; then
        cp "$GITHUB_OUTPUT" "$ARTIFACT_DIR/outputs/github-output.txt"
        log_debug "Copied GITHUB_OUTPUT to artifacts"
    fi
    
    if [[ -n "${GITHUB_ENV:-}" && -f "$GITHUB_ENV" ]]; then
        cp "$GITHUB_ENV" "$ARTIFACT_DIR/outputs/github-env.txt"
        log_debug "Copied GITHUB_ENV to artifacts"
    fi
    
    # Generate diagnostic report
    if command -v "$SCRIPT_DIR/debug/diagnose-workflow.sh" &> /dev/null; then
        bash "$SCRIPT_DIR/debug/diagnose-workflow.sh" report "$ARTIFACT_DIR/diagnostics/workflow-diagnostics.txt"
    fi
    
    # Generate debug report
    generate_debug_report "$ARTIFACT_DIR/diagnostics/debug-report.txt"
    
    # Create artifact summary
    {
        echo "Artifact Collection Summary"
        echo "==========================="
        echo "Timestamp: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
        echo "Location: $ARTIFACT_DIR"
        echo ""
        echo "Collected Items:"
        find "$ARTIFACT_DIR" -type f -printf "  - %P\n" 2>/dev/null | sort
    } | tee "$ARTIFACT_DIR/MANIFEST.txt"
    
    log_info "Artifacts collected at: $ARTIFACT_DIR"
}

# ============================================================================
# Health Check Execution
# ============================================================================

run_with_error_handling() {
    local script_name="$1"
    local script_path="$SCRIPT_DIR/health-check/$script_name"
    
    if [[ ! -f "$script_path" ]]; then
        log_error "Script not found: $script_path"
        return 1
    fi
    
    export WORKFLOW_CONTEXT="$script_name"
    log_info "Running: $script_name"
    
    if $TRACE_EXECUTION; then
        # Run with tracing
        bash -x "$script_path" 2>&1 | while IFS= read -r line; do
            log_trace "$line"
        done
    else
        # Run normally
        bash "$script_path" || {
            local exit_code=$?
            log_error "$script_name failed with exit code: $exit_code"
            return $exit_code
        }
    fi
    
    unset WORKFLOW_CONTEXT
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    # Parse arguments
    parse_arguments "$@"
    
    # Initialize environment
    initialize_artifacts
    
    log_info "=========================================="
    log_info "Health Check with Enhanced Debugging"
    log_info "=========================================="
    log_info "Verbose Mode: $VERBOSE"
    log_info "Diagnostics: $DIAGNOSE"
    log_info "Trace: $TRACE_EXECUTION"
    log_info "Save Artifacts: $SAVE_ARTIFACTS"
    log_info "=========================================="
    echo ""
    
    # Run pre-check diagnostics if requested
    if $DIAGNOSE; then
        log_info "Running pre-check diagnostics..."
        echo ""
        run_full_diagnostics
        echo ""
    fi
    
    # Run health checks
    log_info "Starting health check sequence..."
    echo ""
    
    local checks=(
        "init-monitoring-session.sh"
        "execute-health-checks.sh"
        "record-health-results.sh"
    )
    
    local failed_checks=()
    local passed_checks=()
    
    for check in "${checks[@]}"; do
        if run_with_error_handling "$check"; then
            passed_checks+=("$check")
        else
            failed_checks+=("$check")
        fi
        echo ""
    done
    
    # Collect debug artifacts
    collect_artifacts
    
    # Summary
    log_info "=========================================="
    log_info "Health Check Execution Summary"
    log_info "=========================================="
    log_info "Passed: ${#passed_checks[@]} check(s)"
    for check in "${passed_checks[@]}"; do
        log_info "  ✓ $check"
    done
    
    if (( ${#failed_checks[@]} > 0 )); then
        log_error "Failed: ${#failed_checks[@]} check(s)"
        for check in "${failed_checks[@]}"; do
            log_error "  ✗ $check"
        done
    else
        log_info "Failed: 0 check(s)"
    fi
    
    log_info "=========================================="
    
    # Print artifact location if saved
    if $SAVE_ARTIFACTS; then
        echo ""
        log_info "📦 Debug artifacts saved to: $ARTIFACT_DIR"
        log_info "   Run: ls -la $ARTIFACT_DIR"
        log_info "   View logs: cat $ARTIFACT_DIR/logs/health-check.log"
    fi
    
    # Return appropriate exit code
    if (( ${#failed_checks[@]} == 0 )); then
        return 0
    else
        return 1
    fi
}

# Execute
main "$@"

