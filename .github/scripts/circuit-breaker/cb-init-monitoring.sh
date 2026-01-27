#!/bin/bash
# Initialize circuit breaker monitoring session
# Environment: GH_TOKEN must be set

set -euo pipefail

log() { echo "$@" >&2; }

log "🔌 Starting circuit breaker monitoring session..."

MONITORING_SESSION_ID="cb-monitor-$(date +%Y%m%d-%H%M%S)-$(openssl rand -hex 4)"
ACTION="${1:-status}"

# Emit only key=value pairs to stdout so callers can safely append to GITHUB_ENV
printf 'MONITORING_SESSION_ID=%s\n' "$MONITORING_SESSION_ID"
printf 'ACTION=%s\n' "$ACTION"

log "✅ Circuit breaker monitoring session initialized: $MONITORING_SESSION_ID"
log "📊 Action: $ACTION"
