#!/bin/bash
# Enhanced debugging helpers for GitHub Actions workflows
# Provides structured logging, state inspection, and diagnostics

set -o pipefail

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color

# Debug levels
readonly DEBUG_LEVEL_TRACE=5
readonly DEBUG_LEVEL_DEBUG=4
readonly DEBUG_LEVEL_INFO=3
readonly DEBUG_LEVEL_WARN=2
readonly DEBUG_LEVEL_ERROR=1
readonly DEBUG_LEVEL_OFF=0

# Default debug level (can be overridden via WORKFLOW_DEBUG_LEVEL)
DEBUG_LEVEL=${WORKFLOW_DEBUG_LEVEL:-3}

# Debug log file (optional)
DEBUG_LOG_FILE="${DEBUG_LOG_FILE:-/tmp/workflow-debug.log}"

# Create debug directory if it doesn't exist
mkdir -p "$(dirname "$DEBUG_LOG_FILE")"

# ============================================================================
# Structured Logging
# ============================================================================

# Log with timestamp, level, and context
_log() {
    local level=$1
    local level_name=$2
    local level_color=$3
    shift 3
    local message="$@"
    
    local timestamp=$(date -u '+%Y-%m-%dT%H:%M:%S.%3NZ')
    local context="${WORKFLOW_CONTEXT:-main}"
    
    # Format: [TIMESTAMP] [LEVEL] [CONTEXT] Message
    local formatted="[${timestamp}] [${level_name}] [${context}] ${message}"
    
    # Only log if level is appropriate
    if (( level <= DEBUG_LEVEL )); then
        # Print to stderr with color
        echo -e "${level_color}${formatted}${NC}" >&2
        
        # Also log to file if specified
        if [[ -n "$DEBUG_LOG_FILE" ]]; then
            echo "$formatted" >> "$DEBUG_LOG_FILE"
        fi
    fi
}

log_error() {
    _log "$DEBUG_LEVEL_ERROR" "ERROR" "$RED" "$@"
}

log_warn() {
    _log "$DEBUG_LEVEL_WARN" "WARN" "$YELLOW" "$@"
}

log_info() {
    _log "$DEBUG_LEVEL_INFO" "INFO" "$GREEN" "$@"
}

log_debug() {
    _log "$DEBUG_LEVEL_DEBUG" "DEBUG" "$BLUE" "$@"
}

log_trace() {
    _log "$DEBUG_LEVEL_TRACE" "TRACE" "$CYAN" "$@"
}

# ============================================================================
# State Inspection & Diagnostics
# ============================================================================

# Inspect GitHub Actions environment
inspect_github_env() {
    local context="${1:-GitHub Env}"
    export WORKFLOW_CONTEXT="$context"
    
    log_debug "========== GitHub Environment Inspection =========="
    log_debug "Repository: $GITHUB_REPOSITORY"
    log_debug "Ref: $GITHUB_REF"
    log_debug "SHA: $GITHUB_SHA"
    log_debug "Actor: $GITHUB_ACTOR"
    log_debug "Workflow: $GITHUB_WORKFLOW"
    log_debug "Run ID: $GITHUB_RUN_ID"
    log_debug "Run Number: $GITHUB_RUN_NUMBER"
    log_debug "Job ID: $GITHUB_JOB"
    log_debug "Event Name: $GITHUB_EVENT_NAME"
    
    # Check if running in Actions
    if [[ "$GITHUB_ACTIONS" == "true" ]]; then
        log_debug "Running in GitHub Actions: YES"
        log_debug "Runner OS: $RUNNER_OS"
        log_debug "Runner Temp: $RUNNER_TEMP"
        log_debug "Workspace: $GITHUB_WORKSPACE"
    else
        log_warn "Not running in GitHub Actions environment"
    fi
    
    unset WORKFLOW_CONTEXT
}

# Inspect command availability
inspect_tools() {
    local context="Tool Availability"
    export WORKFLOW_CONTEXT="$context"
    
    log_debug "========== Tool Availability Check =========="
    
    local tools=("gh" "git" "curl" "jq" "python3" "bash" "sed" "awk" "grep")
    
    for tool in "${tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            local version=$("$tool" --version 2>&1 | head -n1)
            log_debug "✓ $tool: $version"
        else
            log_warn "✗ $tool: NOT FOUND"
        fi
    done
    
    unset WORKFLOW_CONTEXT
}

# Inspect GitHub CLI configuration
inspect_gh_config() {
    local context="GitHub CLI Config"
    export WORKFLOW_CONTEXT="$context"
    
    log_debug "========== GitHub CLI Configuration =========="
    
    if ! command -v gh &> /dev/null; then
        log_warn "GitHub CLI not installed"
        unset WORKFLOW_CONTEXT
        return 1
    fi
    
    log_debug "GitHub CLI version: $(gh --version)"
    
    # Check if authenticated
    if gh auth status &> /dev/null; then
        log_debug "GitHub CLI authentication: OK"
        
        # Get current user
        local user=$(gh api user --jq '.login' 2>/dev/null || echo "unknown")
        log_debug "Authenticated as: $user"
    else
        log_error "GitHub CLI authentication: FAILED"
        unset WORKFLOW_CONTEXT
        return 1
    fi
    
    unset WORKFLOW_CONTEXT
}

# Inspect variable permissions and state
inspect_variables() {
    local context="Variable State"
    export WORKFLOW_CONTEXT="$context"
    
    log_debug "========== Repository Variables =========="
    
    if ! command -v gh &> /dev/null; then
        log_warn "GitHub CLI not available - skipping variable inspection"
        unset WORKFLOW_CONTEXT
        return 1
    fi
    
    if [[ -z "$GITHUB_REPOSITORY" ]]; then
        log_error "GITHUB_REPOSITORY not set"
        unset WORKFLOW_CONTEXT
        return 1
    fi
    
    # Attempt to list variables and capture permissions error
    local output
    local exit_code=0
    output=$(gh variable list --repo "$GITHUB_REPOSITORY" 2>&1) || exit_code=$?
    
    if (( exit_code == 0 )); then
        log_debug "Variables accessible:"
        while IFS= read -r line; do
            log_debug "  $line"
        done <<< "$output"
    else
        log_error "Cannot access variables (exit code: $exit_code)"
        log_error "Error output:"
        while IFS= read -r line; do
            log_error "  $line"
        done <<< "$output"
        unset WORKFLOW_CONTEXT
        return 1
    fi
    
    unset WORKFLOW_CONTEXT
}

# Inspect workflow permissions
inspect_permissions() {
    local context="Permissions"
    export WORKFLOW_CONTEXT="$context"
    
    log_debug "========== Workflow Permissions =========="
    
    # These are set by GitHub Actions if available
    log_debug "GITHUB_TOKEN available: $([ -n "$GITHUB_TOKEN" ] && echo "YES" || echo "NO")"
    
    # Try to determine actual permissions by attempting operations
    if [[ -n "$GITHUB_REPOSITORY" && -n "$GITHUB_TOKEN" ]]; then
        log_debug "Testing permission levels..."
        
        # Test variable read (requires vars:read or actions:read)
        if gh variable list --repo "$GITHUB_REPOSITORY" &> /dev/null; then
            log_debug "  ✓ Can read variables"
        else
            log_warn "  ✗ Cannot read variables"
        fi
        
        # Test workflow write (requires actions:write)
        if gh workflow view health-monitor --repo "$GITHUB_REPOSITORY" &> /dev/null; then
            log_debug "  ✓ Can read workflows"
        else
            log_warn "  ✗ Cannot read workflows"
        fi
    else
        log_warn "Missing GITHUB_REPOSITORY or GITHUB_TOKEN - cannot test permissions"
    fi
    
    unset WORKFLOW_CONTEXT
}

# Inspect step outputs and environment variables
inspect_step_outputs() {
    local context="Step Outputs"
    export WORKFLOW_CONTEXT="$context"
    
    log_debug "========== Step Environment Variables =========="
    
    # Show all GITHUB_OUTPUT related variables
    log_debug "GITHUB_OUTPUT: ${GITHUB_OUTPUT:-not set}"
    log_debug "GITHUB_ENV: ${GITHUB_ENV:-not set}"
    log_debug "GITHUB_STEP_SUMMARY: ${GITHUB_STEP_SUMMARY:-not set}"
    
    # Check if output file exists and is readable
    if [[ -n "$GITHUB_OUTPUT" && -f "$GITHUB_OUTPUT" ]]; then
        log_debug "Output file contents:"
        while IFS= read -r line; do
            # Mask secrets
            if [[ "$line" =~ [Ss]ecret|[Pp]assword|[Tt]oken ]]; then
                log_debug "  [REDACTED]"
            else
                log_debug "  $line"
            fi
        done < "$GITHUB_OUTPUT"
    else
        log_warn "Output file not accessible or doesn't exist"
    fi
    
    unset WORKFLOW_CONTEXT
}

# ============================================================================
# Error Diagnostics
# ============================================================================

# Diagnose GitHub variable operation failure
diagnose_variable_failure() {
    local var_name="$1"
    local operation="$2"
    
    local context="Variable Failure Diagnosis"
    export WORKFLOW_CONTEXT="$context"
    
    log_error "========== Diagnosing Variable $operation Failure =========="
    log_error "Variable: $var_name"
    log_error "Operation: $operation"
    
    # Check prerequisites
    if ! command -v gh &> /dev/null; then
        log_error "Root Cause: GitHub CLI not installed"
        unset WORKFLOW_CONTEXT
        return 1
    fi
    
    if ! gh auth status &> /dev/null; then
        log_error "Root Cause: GitHub CLI authentication failed"
        unset WORKFLOW_CONTEXT
        return 1
    fi
    
    if [[ -z "$GITHUB_REPOSITORY" ]]; then
        log_error "Root Cause: GITHUB_REPOSITORY not set"
        unset WORKFLOW_CONTEXT
        return 1
    fi
    
    # Try the operation and capture error
    local test_cmd="gh variable list --repo $GITHUB_REPOSITORY"
    local output
    local exit_code=0
    
    output=$($test_cmd 2>&1) || exit_code=$?
    
    log_error "Test command: $test_cmd"
    log_error "Exit code: $exit_code"
    
    if (( exit_code != 0 )); then
        log_error "Error output:"
        while IFS= read -r line; do
            log_error "  $line"
        done <<< "$output"
    fi
    
    # Parse error message for specific permission issues
    if echo "$output" | grep -q "403"; then
        log_error "Likely Cause: Permission denied (HTTP 403)"
        log_error "Solution: Check job permissions in workflow file:"
        log_error "  - Ensure 'vars: write' or 'actions: write' in permissions section"
        log_error "  - Check repository settings for workflow permissions"
    elif echo "$output" | grep -q "404"; then
        log_error "Likely Cause: Repository or variable not found"
        log_error "Solution: Verify GITHUB_REPOSITORY is correct"
    elif echo "$output" | grep -q "authentication"; then
        log_error "Likely Cause: Authentication failed"
        log_error "Solution: Verify GITHUB_TOKEN is valid"
    fi
    
    unset WORKFLOW_CONTEXT
}

# ============================================================================
# Execution Tracing
# ============================================================================

# Enable detailed execution tracing
enable_trace_mode() {
    log_info "Enabling detailed trace mode"
    set -x  # Print each command before executing
    DEBUG_LEVEL=$DEBUG_LEVEL_TRACE
}

# Disable trace mode
disable_trace_mode() {
    log_info "Disabling trace mode"
    set +x
}

# Trace function execution
trace_function() {
    local func_name="$1"
    local start_time=$(date +%s%N)
    
    export WORKFLOW_CONTEXT="$func_name"
    log_trace "→ Entering function: $func_name"
    
    # Store for later (in a trap)
    export _TRACE_FUNC_START=$start_time
}

trace_function_exit() {
    local func_name="${WORKFLOW_CONTEXT:-unknown}"
    local start_time=${_TRACE_FUNC_START:-0}
    local end_time=$(date +%s%N)
    
    if (( start_time > 0 )); then
        local duration=$(( (end_time - start_time) / 1000000 ))
        log_trace "← Exiting function: $func_name (${duration}ms)"
    else
        log_trace "← Exiting function: $func_name"
    fi
    
    unset WORKFLOW_CONTEXT
    unset _TRACE_FUNC_START
}

# ============================================================================
# Debug Report Generation
# ============================================================================

# Generate comprehensive debug report
generate_debug_report() {
    local report_file="${1:-/tmp/workflow-debug-report.txt}"
    
    log_info "Generating comprehensive debug report..."
    
    {
        echo "=========================================="
        echo "GitHub Actions Workflow Debug Report"
        echo "Generated: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
        echo "=========================================="
        echo ""
        
        echo "## Environment Information"
        echo "Repository: $GITHUB_REPOSITORY"
        echo "Workflow: $GITHUB_WORKFLOW"
        echo "Run ID: $GITHUB_RUN_ID"
        echo "Runner OS: $RUNNER_OS"
        echo ""
        
        echo "## Tool Versions"
        gh --version 2>/dev/null || echo "gh: NOT INSTALLED"
        git --version 2>/dev/null || echo "git: NOT INSTALLED"
        python3 --version 2>/dev/null || echo "python3: NOT INSTALLED"
        echo ""
        
        echo "## Environment Variables (selected)"
        env | grep -E "^(GITHUB|RUNNER|WORKFLOW)" | sort || echo "No matching env vars"
        echo ""
        
        echo "## GitHub Token Status"
        if [[ -n "$GITHUB_TOKEN" ]]; then
            echo "GITHUB_TOKEN: SET (length: ${#GITHUB_TOKEN})"
            if gh auth status &> /dev/null; then
                echo "Authentication: OK"
            else
                echo "Authentication: FAILED"
            fi
        else
            echo "GITHUB_TOKEN: NOT SET"
        fi
        echo ""
        
    } | tee "$report_file"
    
    log_info "Debug report saved to: $report_file"
}

# Export all functions
export -f log_error log_warn log_info log_debug log_trace
export -f inspect_github_env inspect_tools inspect_gh_config
export -f inspect_variables inspect_permissions inspect_step_outputs
export -f diagnose_variable_failure
export -f enable_trace_mode disable_trace_mode
export -f trace_function trace_function_exit
export -f generate_debug_report

