#!/bin/bash
# Manual deployment/rollback action logging and validation
# Extracted from deploy.yml

set -e

echo "🔧 Manual deployment/rollback initiated - logging action details..."

# Initialize manual action tracking
MANUAL_ACTION_TYPE="deployment"
MANUAL_ACTOR="$GITHUB_ACTOR"
MANUAL_TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
MANUAL_REASON="$INPUT_MANUAL_REASON"
BYPASS_GATING="$INPUT_BYPASS_GATING"
OVERRIDE_CIRCUIT_BREAKER="$INPUT_OVERRIDE_CIRCUIT_BREAKER"
FORCE_DEPLOYMENT="$INPUT_FORCE_DEPLOYMENT"
IS_ROLLBACK="$INPUT_ROLLBACK"
ARTIFACT_DIGEST="$INPUT_ARTIFACT_DIGEST"

# Determine action type
if [ "$IS_ROLLBACK" = "true" ]; then
  MANUAL_ACTION_TYPE="rollback"
fi

echo "=== MANUAL ACTION DETAILS ==="
echo "Action Type: $MANUAL_ACTION_TYPE"
echo "Actor: $MANUAL_ACTOR"
echo "Timestamp: $MANUAL_TIMESTAMP"
echo "Reason: ${MANUAL_REASON:-'Not provided'}"
echo "Bypass Gating: $BYPASS_GATING"
echo "Override Circuit Breaker: $OVERRIDE_CIRCUIT_BREAKER"
echo "Force Deployment: $FORCE_DEPLOYMENT"
echo "Artifact Digest: ${ARTIFACT_DIGEST:-'Auto-select'}"

# Validate manual reason for sensitive operations
if [ "$BYPASS_GATING" = "true" ] || [ "$OVERRIDE_CIRCUIT_BREAKER" = "true" ]; then
  if [ -z "$MANUAL_REASON" ] || [ "$MANUAL_REASON" = "null" ]; then
    echo "❌ Manual reason is required when bypassing gating or overriding circuit breaker"
    echo "Please provide a clear reason for this manual intervention"
    exit 1
  fi
  
  if [ ${#MANUAL_REASON} -lt 10 ]; then
    echo "❌ Manual reason must be at least 10 characters for sensitive operations"
    echo "Please provide a detailed reason for this manual intervention"
    exit 1
  fi
fi

# Log manual action to GitHub variables for audit trail
gh variable set LAST_MANUAL_ACTION_TYPE --body "$MANUAL_ACTION_TYPE" --repo "$GITHUB_REPOSITORY"
gh variable set LAST_MANUAL_ACTION_ACTOR --body "$MANUAL_ACTOR" --repo "$GITHUB_REPOSITORY"
gh variable set LAST_MANUAL_ACTION_TIMESTAMP --body "$MANUAL_TIMESTAMP" --repo "$GITHUB_REPOSITORY"
gh variable set LAST_MANUAL_ACTION_REASON --body "${MANUAL_REASON:-'Not provided'}" --repo "$GITHUB_REPOSITORY"
gh variable set LAST_MANUAL_ACTION_BYPASS_GATING --body "$BYPASS_GATING" --repo "$GITHUB_REPOSITORY"
gh variable set LAST_MANUAL_ACTION_OVERRIDE_CB --body "$OVERRIDE_CIRCUIT_BREAKER" --repo "$GITHUB_REPOSITORY"
gh variable set LAST_MANUAL_ACTION_FORCE --body "$FORCE_DEPLOYMENT" --repo "$GITHUB_REPOSITORY"

# Create detailed manual action log entry
MANUAL_ACTION_LOG="{\"action_type\":\"$MANUAL_ACTION_TYPE\",\"actor\":\"$MANUAL_ACTOR\",\"timestamp\":\"$MANUAL_TIMESTAMP\",\"reason\":\"${MANUAL_REASON:-'Not provided'}\",\"bypass_gating\":$BYPASS_GATING,\"override_circuit_breaker\":$OVERRIDE_CIRCUIT_BREAKER,\"force_deployment\":$FORCE_DEPLOYMENT,\"artifact_digest\":\"${ARTIFACT_DIGEST:-'auto-select'}\",\"workflow_run_id\":\"$GITHUB_RUN_ID\",\"workflow_run_url\":\"$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID\"}"

# Store detailed log for audit purposes
gh variable set LAST_MANUAL_ACTION_DETAILS --body "$MANUAL_ACTION_LOG" --repo "$GITHUB_REPOSITORY"

# Set outputs for later steps
echo "MANUAL_ACTION_TYPE=$MANUAL_ACTION_TYPE" >> "$GITHUB_ENV"
echo "MANUAL_ACTOR=$MANUAL_ACTOR" >> "$GITHUB_ENV"
echo "MANUAL_TIMESTAMP=$MANUAL_TIMESTAMP" >> "$GITHUB_ENV"
echo "MANUAL_REASON=${MANUAL_REASON:-'Not provided'}" >> "$GITHUB_ENV"
echo "BYPASS_GATING=$BYPASS_GATING" >> "$GITHUB_ENV"
echo "OVERRIDE_CIRCUIT_BREAKER=$OVERRIDE_CIRCUIT_BREAKER" >> "$GITHUB_ENV"
echo "FORCE_DEPLOYMENT=$FORCE_DEPLOYMENT" >> "$GITHUB_ENV"

echo "✅ Manual action logged and validated successfully"

# Add manual action summary to GitHub step summary
{
  echo "## 🔧 Manual Action Initiated"
  echo ""
  echo "### Action Details"
  echo "- **Type**: $MANUAL_ACTION_TYPE"
  echo "- **Actor**: $MANUAL_ACTOR"
  echo "- **Timestamp**: $MANUAL_TIMESTAMP"
  echo "- **Reason**: ${MANUAL_REASON:-'Not provided'}"
  echo ""
  echo "### Override Flags"
  echo "- **Bypass Gating**: $([ "$BYPASS_GATING" = "true" ] && echo "⚠️ YES" || echo "❌ NO")"
  echo "- **Override Circuit Breaker**: $([ "$OVERRIDE_CIRCUIT_BREAKER" = "true" ] && echo "🚨 YES" || echo "❌ NO")"
  echo "- **Force Deployment**: $([ "$FORCE_DEPLOYMENT" = "true" ] && echo "⚠️ YES" || echo "❌ NO")"
  echo ""
  
  if [ "$BYPASS_GATING" = "true" ] || [ "$OVERRIDE_CIRCUIT_BREAKER" = "true" ]; then
    echo "### ⚠️ Safety Override Warning"
    echo "This manual action includes safety overrides. Ensure you understand the implications:"
    echo "- Bypassing gating may deploy untested artifacts"
    echo "- Overriding circuit breaker may repeat failed operations"
    echo "- Manual intervention responsibility lies with the operator"
    echo ""
  fi
} >> "$GITHUB_STEP_SUMMARY"
