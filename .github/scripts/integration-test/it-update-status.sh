#!/bin/bash
# Update artifact status to testing
# Arguments: $1 - artifact digest

set -euo pipefail

DIGEST=$1

echo "📝 Marking artifact as under integration testing..."
python scripts/artifact_manager.py update-status \
  --digest "$DIGEST" \
  --status testing \
  --timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
