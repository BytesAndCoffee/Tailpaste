#!/bin/bash
# Generate circuit breaker monitoring summary
# Arguments: Pass all status outputs as environment variables

set -euo pipefail

echo "📋 Generating circuit breaker monitoring summary..."

# Create comprehensive summary
echo "## 🔌 Circuit Breaker Monitoring Report" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY
echo "### Monitoring Session" >> $GITHUB_STEP_SUMMARY
echo "- **Session ID**: \`$MONITORING_SESSION_ID\`" >> $GITHUB_STEP_SUMMARY
echo "- **Timestamp**: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> $GITHUB_STEP_SUMMARY
echo "- **Action**: $ACTION" >> $GITHUB_STEP_SUMMARY
echo "- **Triggered By**: ${TRIGGER_SOURCE:-Unknown}" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

echo "### Circuit Breaker Status" >> $GITHUB_STEP_SUMMARY

# Status with emoji
case "$CB_STATUS" in
  "open")
    echo "- **Status**: 🚫 **OPEN** - Manual intervention required" >> $GITHUB_STEP_SUMMARY
    ;;
  "closed")
    echo "- **Status**: ✅ **CLOSED** - Normal operation" >> $GITHUB_STEP_SUMMARY
    ;;
  *)
    echo "- **Status**: ❓ **$CB_STATUS** - Unknown state" >> $GITHUB_STEP_SUMMARY
    ;;
esac

echo "" >> $GITHUB_STEP_SUMMARY
echo "### Failure Counts" >> $GITHUB_STEP_SUMMARY
echo "- **Recovery Failures**: $RECOVERY_FAILURES / $RECOVERY_THRESHOLD $([ "$RECOVERY_EXCEEDED" = "true" ] && echo "🚫 **EXCEEDED**" || echo "✅ Within limit")" >> $GITHUB_STEP_SUMMARY
echo "- **Deployment Failures**: $DEPLOYMENT_FAILURES / $DEPLOYMENT_THRESHOLD $([ "$DEPLOYMENT_EXCEEDED" = "true" ] && echo "🚫 **EXCEEDED**" || echo "✅ Within limit")" >> $GITHUB_STEP_SUMMARY

echo "" >> $GITHUB_STEP_SUMMARY
echo "### Recommendations" >> $GITHUB_STEP_SUMMARY

if [ "$CB_STATUS" = "open" ]; then
  echo "#### 🚨 Circuit Breaker is Open" >> $GITHUB_STEP_SUMMARY
  echo "1. 🔍 **Investigate root cause** of repeated failures" >> $GITHUB_STEP_SUMMARY
  echo "2. 🛠️ **Fix underlying issues** manually" >> $GITHUB_STEP_SUMMARY
  echo "3. 🧪 **Test systems** manually to verify fixes" >> $GITHUB_STEP_SUMMARY
  echo "4. 🔄 **Reset circuit breaker** using manual workflow trigger" >> $GITHUB_STEP_SUMMARY
elif [ "$RECOVERY_EXCEEDED" = "true" ] || [ "$DEPLOYMENT_EXCEEDED" = "true" ]; then
  echo "#### ⚠️  Thresholds Exceeded" >> $GITHUB_STEP_SUMMARY
  echo "1. 🔍 **Monitor system closely** for additional failures" >> $GITHUB_STEP_SUMMARY
  echo "2. 🛠️ **Address root causes** before circuit breaker opens automatically" >> $GITHUB_STEP_SUMMARY
  echo "3. 📊 **Review failure patterns** to identify systemic issues" >> $GITHUB_STEP_SUMMARY
else
  echo "#### ✅ System Healthy" >> $GITHUB_STEP_SUMMARY
  echo "- Circuit breaker is functioning normally" >> $GITHUB_STEP_SUMMARY
  echo "- All failure counts are within acceptable thresholds" >> $GITHUB_STEP_SUMMARY
  echo "- Continue normal monitoring" >> $GITHUB_STEP_SUMMARY
fi

echo "" >> $GITHUB_STEP_SUMMARY
echo "### Quick Actions" >> $GITHUB_STEP_SUMMARY
echo "- **View Status**: Run this workflow with 'status' action" >> $GITHUB_STEP_SUMMARY
echo "- **Check Thresholds**: Run this workflow with 'check-thresholds' action" >> $GITHUB_STEP_SUMMARY
echo "- **Reset Circuit Breaker**: Run this workflow with 'reset' action" >> $GITHUB_STEP_SUMMARY
echo "- **Export Logs**: Run this workflow with 'export-logs' action" >> $GITHUB_STEP_SUMMARY

echo "" >> $GITHUB_STEP_SUMMARY
echo "---" >> $GITHUB_STEP_SUMMARY
echo "*🔄 Next monitoring check scheduled in 1 hour*" >> $GITHUB_STEP_SUMMARY

echo "✅ Circuit breaker monitoring summary generated"
