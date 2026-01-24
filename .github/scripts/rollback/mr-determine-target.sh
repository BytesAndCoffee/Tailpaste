#!/bin/bash
# Determine rollback target artifact

set -e

echo "🎯 Determining rollback target artifact..."

TARGET_DIGEST=""

case "$ROLLBACK_TARGET" in
  "latest-backup")
    echo "📦 Using latest backup artifact..."
    TARGET_DIGEST=$(gh variable get BACKUP_ARTIFACT_DIGEST --repo "$GITHUB_REPOSITORY" 2>/dev/null || echo "")
    
    if [ -z "$TARGET_DIGEST" ]; then
      echo "❌ No backup artifact digest found"
      echo "Cannot perform digest-based rollback to latest backup"
      echo "Consider using 'file-based' rollback target instead"
      exit 1
    fi
    
    echo "✅ Latest backup artifact: $TARGET_DIGEST"
    ;;
    
  "specific-digest")
    echo "🎯 Using specific artifact digest..."
    TARGET_DIGEST="$ARTIFACT_DIGEST"
    
    # Validate the specific digest exists in registry
    if ! python scripts/ci/artifact_manager.py validate-digest --digest "$TARGET_DIGEST" --registry "$REGISTRY" --repository "$IMAGE_NAME"; then
      echo "❌ Specified artifact digest not found in registry: $TARGET_DIGEST"
      exit 1
    fi
    
    echo "✅ Specific artifact validated: $TARGET_DIGEST"
    ;;
    
  "file-based")
    echo "📁 Using file-based rollback..."
    echo "Will use local backup files instead of registry artifacts"
    TARGET_DIGEST=""
    ;;
    
  *)
    echo "❌ Unknown rollback target: $ROLLBACK_TARGET"
    exit 1
    ;;
esac

# Record rollback target information
gh variable set MANUAL_ROLLBACK_TARGET_DIGEST --body "${TARGET_DIGEST:-'file-based'}" --repo "$GITHUB_REPOSITORY"

echo "TARGET_DIGEST=${TARGET_DIGEST}" >> "$GITHUB_ENV"
echo "✅ Rollback target determined successfully"
