#!/bin/bash
# Release rollback lock

set -e

echo "🔓 Releasing rollback lock..."

# Clear rollback lock
gh variable set ROLLBACK_IN_PROGRESS --body "false" --repo "$GITHUB_REPOSITORY"
gh variable delete ROLLBACK_STARTED_BY --repo "$GITHUB_REPOSITORY" 2>/dev/null || true
gh variable delete ROLLBACK_STARTED_AT --repo "$GITHUB_REPOSITORY" 2>/dev/null || true
gh variable delete ROLLBACK_WORKFLOW_RUN_ID --repo "$GITHUB_REPOSITORY" 2>/dev/null || true

echo "✅ Rollback lock released"
