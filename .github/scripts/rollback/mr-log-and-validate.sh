#!/bin/bash
# Log manual rollback initiation and validate inputs

set -e

echo "🔄 Manual rollback initiated - logging action details..."

# Initialize manual rollback tracking
ROLLBACK_ACTOR="$GITHUB_ACTOR"
ROLLBACK_TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
ROLLBACK_REASON="$INPUT_ROLLBACK_REASON"
ROLLBACK_TARGET="$INPUT_ROLLBACK_TARGET"
ARTIFACT_DIGEST="$INPUT_ARTIFACT_DIGEST"
BYPASS_VERIFICATION="$INPUT_BYPASS_VERIFICATION"
BYPASS_HEALTH_CHECKS="$INPUT_BYPASS_HEALTH_CHECKS"
EMERGENCY_ROLLBACK="$INPUT_EMERGENCY_ROLLBACK"
SKIP_BACKUP="$INPUT_SKIP_BACKUP"

echo "=== MANUAL ROLLBACK DETAILS ==="
echo "Actor: $ROLLBACK_ACTOR"
echo "Timestamp: $ROLLBACK_TIMESTAMP"
echo "Reason: $ROLLBACK_REASON"
echo "Target: $ROLLBACK_TARGET"
echo "Artifact Digest: ${ARTIFACT_DIGEST:-'Auto-select'}"
echo "Bypass Verification: $BYPASS_VERIFICATION"
echo "Bypass Health Checks: $BYPASS_HEALTH_CHECKS"
echo "Emergency Rollback: $EMERGENCY_ROLLBACK"
echo "Skip Backup: $SKIP_BACKUP"

# Validate rollback reason
if [ -z "$ROLLBACK_REASON" ] || [ "$ROLLBACK_REASON" = "null" ]; then
  echo "❌ Rollback reason is required for all manual rollbacks"
  echo "Please provide a clear reason for this rollback operation"
  exit 1
fi

if [ ${#ROLLBACK_REASON} -lt 10 ]; then
  echo "❌ Rollback reason must be at least 10 characters"
  echo "Please provide a detailed reason for this rollback operation"
  exit 1
fi

# Validate specific digest if provided
if [ "$ROLLBACK_TARGET" = "specific-digest" ]; then
  if [ -z "$ARTIFACT_DIGEST" ] || [ "$ARTIFACT_DIGEST" = "null" ]; then
    echo "❌ Artifact digest is required when rollback target is 'specific-digest'"
    echo "Please provide a valid artifact digest"
    exit 1
  fi
  
  # Validate digest format
  if ! echo "$ARTIFACT_DIGEST" | grep -qE "^sha256:[a-f0-9]{64}$"; then
    echo "❌ Invalid artifact digest format: $ARTIFACT_DIGEST"
    echo "Expected format: sha256:64-character-hex-string"
    exit 1
  fi
fi

# Validate emergency rollback requirements
if [ "$EMERGENCY_ROLLBACK" = "true" ]; then
  if [ ${#ROLLBACK_REASON} -lt 20 ]; then
    echo "❌ Emergency rollback requires a detailed reason (minimum 20 characters)"
    echo "Please provide a comprehensive explanation for the emergency rollback"
    exit 1
  fi
  
  echo "🚨 EMERGENCY ROLLBACK ACTIVATED"
  echo "⚠️  All safety checks will be bypassed"
  echo "🔧 Emergency operator: $ROLLBACK_ACTOR"
  echo "📝 Emergency reason: $ROLLBACK_REASON"
  echo ""
  echo "🚨 CRITICAL SAFETY WARNINGS:"
  echo "- All automated safety mechanisms will be disabled"
  echo "- Rollback verification will be skipped"
  echo "- Health checks will be bypassed"
  echo "- This is for emergency use only"
  echo "- Monitor the system closely after rollback"
  echo "- Be prepared for immediate manual intervention"
  
  # Override other bypass flags for emergency rollback
  BYPASS_VERIFICATION="true"
  BYPASS_HEALTH_CHECKS="true"
fi

# Log comprehensive manual rollback action
gh variable set MANUAL_ROLLBACK_INITIATED_BY --body "$ROLLBACK_ACTOR" --repo "$GITHUB_REPOSITORY"
gh variable set MANUAL_ROLLBACK_INITIATED_AT --body "$ROLLBACK_TIMESTAMP" --repo "$GITHUB_REPOSITORY"
gh variable set MANUAL_ROLLBACK_REASON --body "$ROLLBACK_REASON" --repo "$GITHUB_REPOSITORY"
gh variable set MANUAL_ROLLBACK_TARGET --body "$ROLLBACK_TARGET" --repo "$GITHUB_REPOSITORY"
gh variable set MANUAL_ROLLBACK_BYPASS_VERIFICATION --body "$BYPASS_VERIFICATION" --repo "$GITHUB_REPOSITORY"
gh variable set MANUAL_ROLLBACK_BYPASS_HEALTH_CHECKS --body "$BYPASS_HEALTH_CHECKS" --repo "$GITHUB_REPOSITORY"
gh variable set MANUAL_ROLLBACK_EMERGENCY --body "$EMERGENCY_ROLLBACK" --repo "$GITHUB_REPOSITORY"
gh variable set MANUAL_ROLLBACK_SKIP_BACKUP --body "$SKIP_BACKUP" --repo "$GITHUB_REPOSITORY"

# Create detailed manual rollback audit log
MANUAL_ROLLBACK_AUDIT="{\"rollback_type\":\"manual_rollback_workflow\",\"actor\":\"$ROLLBACK_ACTOR\",\"timestamp\":\"$ROLLBACK_TIMESTAMP\",\"reason\":\"$ROLLBACK_REASON\",\"target\":\"$ROLLBACK_TARGET\",\"artifact_digest\":\"${ARTIFACT_DIGEST:-'auto-select'}\",\"bypass_verification\":$BYPASS_VERIFICATION,\"bypass_health_checks\":$BYPASS_HEALTH_CHECKS,\"emergency_rollback\":$EMERGENCY_ROLLBACK,\"skip_backup\":$SKIP_BACKUP,\"workflow_run_id\":\"$GITHUB_RUN_ID\",\"workflow_run_url\":\"$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID\"}"

gh variable set MANUAL_ROLLBACK_AUDIT --body "$MANUAL_ROLLBACK_AUDIT" --repo "$GITHUB_REPOSITORY"

# Set outputs for later steps
echo "ROLLBACK_ACTOR=$ROLLBACK_ACTOR" >> "$GITHUB_ENV"
echo "ROLLBACK_TIMESTAMP=$ROLLBACK_TIMESTAMP" >> "$GITHUB_ENV"
echo "ROLLBACK_REASON=$ROLLBACK_REASON" >> "$GITHUB_ENV"
echo "ROLLBACK_TARGET=$ROLLBACK_TARGET" >> "$GITHUB_ENV"
echo "ARTIFACT_DIGEST=${ARTIFACT_DIGEST}" >> "$GITHUB_ENV"
echo "BYPASS_VERIFICATION=$BYPASS_VERIFICATION" >> "$GITHUB_ENV"
echo "BYPASS_HEALTH_CHECKS=$BYPASS_HEALTH_CHECKS" >> "$GITHUB_ENV"
echo "EMERGENCY_ROLLBACK=$EMERGENCY_ROLLBACK" >> "$GITHUB_ENV"
echo "SKIP_BACKUP=$SKIP_BACKUP" >> "$GITHUB_ENV"

echo "✅ Manual rollback logged and validated successfully"

# Add manual rollback summary to GitHub step summary
{
  echo "## 🔄 Manual Rollback Initiated"
  echo ""
  echo "### Rollback Details"
  echo "- **Operator**: $ROLLBACK_ACTOR"
  echo "- **Timestamp**: $ROLLBACK_TIMESTAMP"
  echo "- **Reason**: $ROLLBACK_REASON"
  echo "- **Target**: $ROLLBACK_TARGET"
  echo "- **Artifact**: ${ARTIFACT_DIGEST:-'Auto-select'}"
  echo ""
  echo "### Safety Overrides"
  echo "- **Bypass Verification**: $([ "$BYPASS_VERIFICATION" = "true" ] && echo "⚠️ YES" || echo "❌ NO")"
  echo "- **Bypass Health Checks**: $([ "$BYPASS_HEALTH_CHECKS" = "true" ] && echo "⚠️ YES" || echo "❌ NO")"
  echo "- **Emergency Rollback**: $([ "$EMERGENCY_ROLLBACK" = "true" ] && echo "🚨 YES" || echo "❌ NO")"
  echo "- **Skip Backup**: $([ "$SKIP_BACKUP" = "true" ] && echo "⚠️ YES" || echo "❌ NO")"
  echo ""
  
  if [ "$EMERGENCY_ROLLBACK" = "true" ] || [ "$BYPASS_VERIFICATION" = "true" ] || [ "$BYPASS_HEALTH_CHECKS" = "true" ]; then
    echo "### 🚨 Emergency/Bypass Warning"
    echo "This manual rollback includes safety bypasses. Ensure you understand the implications:"
    echo "- Bypassing verification may skip important safety checks"
    echo "- Bypassing health checks may not detect rollback issues"
    echo "- Emergency rollback disables all automated safety mechanisms"
    echo "- Manual monitoring and intervention responsibility lies with the operator"
    echo ""
  fi
} >> "$GITHUB_STEP_SUMMARY"
