#!/bin/bash
# Workflow Diagnostics Script
# Comprehensive tool for diagnosing workflow execution issues

set -euo pipefail

# Import debug helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/debug-helpers.sh"

# ============================================================================
# Main Diagnostic Routine
# ============================================================================

run_full_diagnostics() {
    local context="Full Diagnostics"
    export WORKFLOW_CONTEXT="$context"
    
    log_info "=========================================="
    log_info "Running Full Workflow Diagnostics"
    log_info "=========================================="
    log_info ""
    
    # Run all inspection functions
    log_info "1. Inspecting GitHub Actions environment..."
    inspect_github_env "Environment" || log_warn "Environment inspection had issues"
    echo ""
    
    log_info "2. Checking tool availability..."
    inspect_tools || log_warn "Tool inspection had issues"
    echo ""
    
    log_info "3. Inspecting GitHub CLI configuration..."
    inspect_gh_config || log_warn "GitHub CLI inspection had issues"
    echo ""
    
    log_info "4. Checking workflow permissions..."
    inspect_permissions || log_warn "Permission inspection had issues"
    echo ""
    
    log_info "5. Inspecting repository variables..."
    inspect_variables || log_warn "Variable inspection had issues"
    echo ""
    
    log_info "6. Checking step outputs..."
    inspect_step_outputs || log_warn "Step output inspection had issues"
    echo ""
    
    log_info "=========================================="
    log_info "Diagnostics Complete"
    log_info "=========================================="
    
    unset WORKFLOW_CONTEXT
}

# Run diagnostics for specific failure
diagnose_issue() {
    local issue_type="$1"
    
    case "$issue_type" in
        variable)
            diagnose_variable_failure "${2:-UNKNOWN}" "${3:-UNKNOWN}"
            ;;
        permissions)
            inspect_permissions
            ;;
        github-cli)
            inspect_gh_config
            ;;
        tools)
            inspect_tools
            ;;
        environment)
            inspect_github_env "Diagnostic"
            ;;
        *)
            log_error "Unknown issue type: $issue_type"
            log_info "Valid issue types: variable, permissions, github-cli, tools, environment"
            return 1
            ;;
    esac
}

# Generate detailed debug output
generate_diagnostics() {
    local output_file="${1:-/tmp/workflow-diagnostics.txt}"
    
    log_info "Generating detailed diagnostics report..."
    
    {
        echo "╔════════════════════════════════════════════════════════════╗"
        echo "║        GitHub Actions Workflow Diagnostics Report          ║"
        echo "╚════════════════════════════════════════════════════════════╝"
        echo ""
        echo "Generated: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
        echo ""
        
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "1. GITHUB ACTIONS ENVIRONMENT"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        if [[ "$GITHUB_ACTIONS" == "true" ]]; then
            echo "✓ Running in GitHub Actions"
            echo "  Repository: $GITHUB_REPOSITORY"
            echo "  Ref: $GITHUB_REF"
            echo "  SHA: ${GITHUB_SHA:0:8}..."
            echo "  Event: $GITHUB_EVENT_NAME"
            echo "  Actor: $GITHUB_ACTOR"
            echo "  Workflow: $GITHUB_WORKFLOW"
            echo "  Run ID: $GITHUB_RUN_ID (#$GITHUB_RUN_NUMBER)"
            echo "  Job: $GITHUB_JOB"
        else
            echo "✗ Not running in GitHub Actions"
        fi
        echo ""
        
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "2. RUNNER ENVIRONMENT"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "OS: $RUNNER_OS"
        echo "Arch: $(uname -m)"
        echo "Runner: $RUNNER_NAME"
        echo "Temp Directory: $RUNNER_TEMP"
        echo "Tool Cache: $RUNNER_TOOL_CACHE"
        echo ""
        
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "3. INSTALLED TOOLS"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        for tool in bash sh zsh python3 python git curl wget jq yq gh; do
            if command -v "$tool" &> /dev/null; then
                version=$("$tool" --version 2>&1 | head -n1)
                printf "%-12s ✓ %s\n" "$tool:" "$version"
            else
                printf "%-12s ✗ NOT FOUND\n" "$tool:"
            fi
        done
        echo ""
        
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "4. GITHUB CLI STATUS"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        if command -v gh &> /dev/null; then
            echo "✓ GitHub CLI installed: $(gh --version)"
            
            if gh auth status &> /dev/null 2>&1; then
                echo "✓ Authentication: OK"
                user=$(gh api user --jq '.login' 2>/dev/null || echo "unknown")
                echo "  Authenticated as: $user"
            else
                echo "✗ Authentication: FAILED"
            fi
        else
            echo "✗ GitHub CLI not installed"
        fi
        echo ""
        
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "5. GITHUB TOKEN STATUS"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        if [[ -n "${GITHUB_TOKEN:-}" ]]; then
            echo "✓ GITHUB_TOKEN is set (${#GITHUB_TOKEN} chars)"
        else
            echo "✗ GITHUB_TOKEN is not set"
        fi
        echo ""
        
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "6. RELEVANT ENVIRONMENT VARIABLES"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        env | grep -E "^(GITHUB|RUNNER|WORKFLOW|CI)" | sort || true
        echo ""
        
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "7. GITHUB OUTPUT/ENV FILES"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
            if [[ -f "$GITHUB_OUTPUT" ]]; then
                echo "GITHUB_OUTPUT file exists at: $GITHUB_OUTPUT"
                echo "Contents:"
                sed 's/=.*/=[REDACTED]/g' "$GITHUB_OUTPUT" | sed 's/^/  /'
            else
                echo "GITHUB_OUTPUT path set but file doesn't exist: $GITHUB_OUTPUT"
            fi
        else
            echo "GITHUB_OUTPUT not set"
        fi
        echo ""
        
        if [[ -n "${GITHUB_ENV:-}" ]]; then
            if [[ -f "$GITHUB_ENV" ]]; then
                echo "GITHUB_ENV file exists at: $GITHUB_ENV"
                echo "Contents:"
                sed 's/=.*/=[REDACTED]/g' "$GITHUB_ENV" | sed 's/^/  /'
            else
                echo "GITHUB_ENV path set but file doesn't exist: $GITHUB_ENV"
            fi
        else
            echo "GITHUB_ENV not set"
        fi
        echo ""
        
    } | tee "$output_file"
    
    log_info "Diagnostics report saved to: $output_file"
}

# ============================================================================
# Script Usage and Help
# ============================================================================

show_usage() {
    cat << 'EOF'
Workflow Diagnostics Script
Usage: ./diagnose-workflow.sh [COMMAND] [OPTIONS]

COMMANDS:
  full                 Run full diagnostic suite
  variable <name>      Diagnose variable operation failure
  permissions          Check workflow permissions
  github-cli           Check GitHub CLI setup
  tools                Check tool availability
  environment          Check GitHub Actions environment
  report [FILE]        Generate detailed diagnostic report
  help                 Show this help message

EXAMPLES:
  ./diagnose-workflow.sh full
  ./diagnose-workflow.sh variable SOME_VAR set
  ./diagnose-workflow.sh report /tmp/my-diagnostics.txt

ENVIRONMENT VARIABLES:
  WORKFLOW_DEBUG_LEVEL  Set debug verbosity (0-5, default: 3)
  DEBUG_LOG_FILE        Log file path (default: /tmp/workflow-debug.log)

EOF
}

# ============================================================================
# Main Entry Point
# ============================================================================

main() {
    local command="${1:-full}"
    
    case "$command" in
        full)
            run_full_diagnostics
            ;;
        report)
            generate_diagnostics "${2:-/tmp/workflow-diagnostics.txt}"
            ;;
        variable)
            diagnose_issue "variable" "${2:-}" "${3:-}"
            ;;
        permissions)
            diagnose_issue "permissions"
            ;;
        github-cli)
            diagnose_issue "github-cli"
            ;;
        tools)
            diagnose_issue "tools"
            ;;
        environment)
            diagnose_issue "environment"
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            log_error "Unknown command: $command"
            show_usage
            return 1
            ;;
    esac
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi

