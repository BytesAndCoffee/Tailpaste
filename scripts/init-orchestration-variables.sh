#!/bin/bash
# Initialize GitHub repository variables for orchestration system
# This script sets up all required variables for the orchestration system to function

set -e

echo "🔧 Initializing GitHub repository variables for orchestration..."
echo ""

# Check if gh CLI is available
if ! command -v gh &> /dev/null; then
    echo "❌ Error: GitHub CLI (gh) is not installed"
    echo "   Install from: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Error: Not authenticated with GitHub CLI"
    echo "   Run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI is available and authenticated"
echo ""

# Get repository from git config or allow override
REPO="${GITHUB_REPOSITORY:-$(git config --get remote.origin.url | sed 's/.*github.com[:/]\(.*\)\.git/\1/')}"

if [ -z "$REPO" ]; then
    echo "❌ Error: Could not determine repository"
    echo "   Set GITHUB_REPOSITORY environment variable or run from a git repository"
    exit 1
fi

echo "📦 Setting variables for repository: $REPO"
echo ""

# Function to set variable with error handling
set_variable() {
    local name=$1
    local value=$2
    local description=$3
    
    echo -n "   Setting $name... "
    if gh variable set "$name" --body "$value" --repo "$REPO" 2>/dev/null; then
        echo "✅"
    else
        echo "⚠️  (may already exist or permission denied)"
    fi
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Health Check & Monitoring Variables"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

set_variable "HEALTH_CHECK_HISTORY" "[]" "History of health check results"
set_variable "HEALTH_CHECK_CONSECUTIVE_DEGRADED" "0" "Count of consecutive degraded health checks"
set_variable "LAST_HEALTH_STATUS" "unknown" "Last recorded health status"
set_variable "LAST_HEALTH_CHECK_TIME" "" "Timestamp of last health check"
set_variable "HEALTH_CHECK_FAILURE_COUNT" "0" "Total health check failures"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Circuit Breaker Variables"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

set_variable "CIRCUIT_BREAKER_STATE" "closed" "Circuit breaker state (closed/open/half-open)"
set_variable "CIRCUIT_BREAKER_FAILURES" "0" "Circuit breaker failure count"
set_variable "CIRCUIT_BREAKER_LAST_FAILURE" "" "Timestamp of last circuit breaker failure"
set_variable "CIRCUIT_BREAKER_OPENED_AT" "" "Timestamp when circuit breaker opened"
set_variable "CIRCUIT_BREAKER_FAILURE_THRESHOLD" "3" "Failure threshold before opening"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Deployment Tracking Variables"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

set_variable "LAST_SUCCESSFUL_DEPLOYMENT" "" "Timestamp of last successful deployment"
set_variable "CURRENT_DEPLOYED_DIGEST" "" "Currently deployed artifact digest"
set_variable "PREVIOUS_DEPLOYED_DIGEST" "" "Previously deployed artifact digest"
set_variable "DEPLOYMENT_COUNT" "0" "Total deployment count"
set_variable "LAST_DEPLOYMENT_STATUS" "" "Status of last deployment"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Orchestration Session Variables"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

set_variable "ORCHESTRATION_SESSION_ID" "" "Current orchestration session ID"
set_variable "ORCHESTRATION_START_TIME" "" "Orchestration session start time"
set_variable "ORCHESTRATION_ACTION" "" "Current orchestration action"
set_variable "ORCHESTRATION_TRIGGER_TYPE" "" "Type of orchestration trigger"
set_variable "ORCHESTRATION_STATUS" "" "Current orchestration status"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Recovery System Variables"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

set_variable "LAST_RECOVERY_ATTEMPT" "" "Timestamp of last recovery attempt"
set_variable "RECOVERY_ATTEMPTS_COUNT" "0" "Total recovery attempts"
set_variable "LAST_RECOVERY_SUCCESS" "" "Timestamp of last successful recovery"
set_variable "LAST_RECOVERY_SESSION_ID" "" "Last recovery session ID"
set_variable "RECOVERY_IN_PROGRESS" "false" "Whether recovery is currently running"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Artifact Management Variables"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

set_variable "LAST_BUILT_COMMIT" "" "Last commit that was built"
set_variable "LAST_TESTED_ARTIFACT" "" "Last artifact that passed testing"
set_variable "ARTIFACT_BUILD_COUNT" "0" "Total artifacts built"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Variable initialization complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "To verify variables were created:"
echo "   gh variable list --repo $REPO"
echo ""
echo "Next steps:"
echo "1. Enable scheduled workflows in GitHub Actions"
echo "2. Run manual test of health monitor"
echo "3. Monitor first scheduled runs"
echo ""
