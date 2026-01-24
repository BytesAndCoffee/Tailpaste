#!/bin/bash
# Generate manual rollback summary

set -e

{
  echo "## 🔄 Manual Rollback Summary"
  echo ""
  
  # Get rollback status
  ROLLBACK_STATUS=$(gh variable get MANUAL_ROLLBACK_STATUS --repo "$GITHUB_REPOSITORY" 2>/dev/null || echo "unknown")
  DEPLOYMENT_RUN_ID=$(gh variable get MANUAL_ROLLBACK_DEPLOYMENT_RUN_ID --repo "$GITHUB_REPOSITORY" 2>/dev/null || echo "")
  
  echo "### Rollback Operation Details"
  echo "- **Status**: $JOB_STATUS"
  echo "- **Rollback Status**: $ROLLBACK_STATUS"
  echo "- **Operator**: $ROLLBACK_ACTOR"
  echo "- **Timestamp**: $ROLLBACK_TIMESTAMP"
  echo "- **Reason**: $ROLLBACK_REASON"
  echo "- **Target**: $ROLLBACK_TARGET"
  
  if [ -n "$TARGET_DIGEST" ]; then
    echo "- **Target Artifact**: \`$TARGET_DIGEST\`"
  fi
  
  if [ -n "$DEPLOYMENT_RUN_ID" ]; then
    echo "- **Deployment Run**: [$DEPLOYMENT_RUN_ID]($GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$DEPLOYMENT_RUN_ID)"
  fi
  
  echo ""
  echo "### Safety Overrides Applied"
  echo "- **Bypass Verification**: $([ "$BYPASS_VERIFICATION" = "true" ] && echo "⚠️ YES" || echo "❌ NO")"
  echo "- **Bypass Health Checks**: $([ "$BYPASS_HEALTH_CHECKS" = "true" ] && echo "⚠️ YES" || echo "❌ NO")"
  echo "- **Emergency Rollback**: $([ "$EMERGENCY_ROLLBACK" = "true" ] && echo "🚨 YES" || echo "❌ NO")"
  echo "- **Skip Backup**: $([ "$SKIP_BACKUP" = "true" ] && echo "⚠️ YES" || echo "❌ NO")"
  
  echo ""
  echo "### Manual Rollback Outcome"
  
  if [ "$JOB_STATUS" = "success" ] && [ "$ROLLBACK_STATUS" = "successful" ]; then
    echo "✅ **Manual rollback completed successfully**"
    echo "- Rollback operation executed without errors"
    echo "- Service should be restored to previous state"
    echo "- Monitor service health to confirm successful rollback"
  elif [ "$EMERGENCY_ROLLBACK" = "true" ] && [ "$ROLLBACK_STATUS" = "emergency_triggered" ]; then
    echo "🚨 **Emergency rollback triggered**"
    echo "- Emergency rollback has been initiated"
    echo "- Monitor the deployment workflow for completion"
    echo "- Verify service health manually after completion"
  else
    echo "❌ **Manual rollback failed or incomplete**"
    echo "- Review logs for specific failure details"
    echo "- Manual intervention may be required"
    echo "- Consider emergency rollback if service is critical"
  fi
  
  echo ""
  echo "### Audit Information"
  echo "This manual rollback operation has been fully logged:"
  echo "- **Workflow Run**: $GITHUB_RUN_ID"
  echo "- **Audit Variables**: \`MANUAL_ROLLBACK_AUDIT\`, \`MANUAL_ROLLBACK_*\`"
  echo "- **Repository**: $GITHUB_REPOSITORY"
  
  echo ""
  echo "---"
  echo "*🔄 Manual rollback operation completed. All actions have been logged for audit and compliance purposes.*"
} >> "$GITHUB_STEP_SUMMARY"
