#!/bin/bash
# Acquire rollback lock with emergency override support

set -e

echo "🔒 Acquiring rollback lock..."

# Check if another rollback is in progress
CURRENT_ROLLBACK=$(gh variable get ROLLBACK_IN_PROGRESS --repo "$GITHUB_REPOSITORY" 2>/dev/null || echo "false")
ROLLBACK_STARTED_BY=$(gh variable get ROLLBACK_STARTED_BY --repo "$GITHUB_REPOSITORY" 2>/dev/null || echo "")
ROLLBACK_STARTED_AT=$(gh variable get ROLLBACK_STARTED_AT --repo "$GITHUB_REPOSITORY" 2>/dev/null || echo "")

if [ "$CURRENT_ROLLBACK" = "true" ]; then
  echo "⚠️  Another rollback is already in progress"
  echo "Started by: $ROLLBACK_STARTED_BY"
  echo "Started at: $ROLLBACK_STARTED_AT"
  
  if [ "$EMERGENCY_ROLLBACK" = "true" ]; then
    echo "🚨 EMERGENCY ROLLBACK OVERRIDE"
    echo "⚠️  Forcing rollback despite concurrent rollback in progress"
    echo "🔧 Emergency operator: $ROLLBACK_ACTOR"
    echo "📝 Emergency reason: $ROLLBACK_REASON"
    echo ""
    echo "🚨 CRITICAL WARNING: This may cause conflicts with the running rollback"
    
    # Log emergency rollback override
    gh variable set EMERGENCY_ROLLBACK_OVERRIDE --body "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --repo "$GITHUB_REPOSITORY"
    gh variable set EMERGENCY_ROLLBACK_OVERRIDE_BY --body "$ROLLBACK_ACTOR" --repo "$GITHUB_REPOSITORY"
    gh variable set EMERGENCY_ROLLBACK_PREVIOUS_ACTOR --body "$ROLLBACK_STARTED_BY" --repo "$GITHUB_REPOSITORY"
    
    echo "⚠️  Proceeding with emergency rollback override"
  else
    echo "❌ Rollback lock is held by another process"
    echo "Options to resolve:"
    echo "1. Wait for the current rollback to complete"
    echo "2. Use 'emergency_rollback' flag if this is truly an emergency"
    echo "3. Manually clear the rollback lock if the previous rollback failed"
    echo ""
    echo "To manually clear a stale lock, run:"
    echo "gh variable set ROLLBACK_IN_PROGRESS --body 'false' --repo $GITHUB_REPOSITORY"
    exit 1
  fi
fi

# Set rollback lock
gh variable set ROLLBACK_IN_PROGRESS --body "true" --repo "$GITHUB_REPOSITORY"
gh variable set ROLLBACK_STARTED_BY --body "$ROLLBACK_ACTOR" --repo "$GITHUB_REPOSITORY"
gh variable set ROLLBACK_STARTED_AT --body "$ROLLBACK_TIMESTAMP" --repo "$GITHUB_REPOSITORY"
gh variable set ROLLBACK_WORKFLOW_RUN_ID --body "$GITHUB_RUN_ID" --repo "$GITHUB_REPOSITORY"

echo "✅ Rollback lock acquired successfully"
echo "Lock holder: $ROLLBACK_ACTOR"
echo "Lock type: Manual Rollback Workflow"
echo "Workflow run: $GITHUB_RUN_ID"
