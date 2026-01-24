#!/bin/bash
# Initialize workflow orchestration session
# Extracted from workflow-orchestrator.yml

set -e

echo "🎼 Initializing workflow orchestration session..."

ORCHESTRATION_SESSION_ID="orchestration-$(date +%Y%m%d-%H%M%S)-$(openssl rand -hex 4)"
ORCHESTRATION_ACTION="${INPUT_ORCHESTRATION_ACTION:-status-check}"
TARGET_WORKFLOW="${INPUT_TARGET_WORKFLOW:-all}"
FORCE_COORDINATION="${INPUT_FORCE_COORDINATION}"
TRIGGER_TYPE="$GITHUB_EVENT_NAME"

echo "ORCHESTRATION_SESSION_ID=$ORCHESTRATION_SESSION_ID" >> "$GITHUB_ENV"
echo "ORCHESTRATION_ACTION=$ORCHESTRATION_ACTION" >> "$GITHUB_ENV"
echo "TARGET_WORKFLOW=$TARGET_WORKFLOW" >> "$GITHUB_ENV"
echo "FORCE_COORDINATION=$FORCE_COORDINATION" >> "$GITHUB_ENV"
echo "TRIGGER_TYPE=$TRIGGER_TYPE" >> "$GITHUB_ENV"

# Record orchestration session start
gh variable set ORCHESTRATION_SESSION_ID --body "$ORCHESTRATION_SESSION_ID" --repo "$GITHUB_REPOSITORY"
gh variable set ORCHESTRATION_START_TIME --body "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --repo "$GITHUB_REPOSITORY"
gh variable set ORCHESTRATION_ACTION --body "$ORCHESTRATION_ACTION" --repo "$GITHUB_REPOSITORY"
gh variable set ORCHESTRATION_TRIGGER_TYPE --body "$TRIGGER_TYPE" --repo "$GITHUB_REPOSITORY"

echo "✅ Orchestration session initialized: $ORCHESTRATION_SESSION_ID"
echo "📊 Session details:"
echo "  - Action: $ORCHESTRATION_ACTION"
echo "  - Target: $TARGET_WORKFLOW"
echo "  - Trigger: $TRIGGER_TYPE"
echo "  - Force: $FORCE_COORDINATION"
