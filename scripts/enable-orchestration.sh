#!/bin/bash
# Script to enable GitHub Actions scheduled workflows for orchestration

set -e

echo "🎼 GitHub Actions Orchestration System - Activation Guide"
echo "=========================================================="
echo ""
echo "Your orchestration system has the following components:"
echo ""
echo "📋 PRIMARY PIPELINE (Already Working):"
echo "   CI → Integration Tests → Deploy"
echo ""
echo "📋 ORCHESTRATION & MONITORING (Needs Activation):"
echo "   1. Health Monitor (runs every 5 minutes)"
echo "   2. Workflow Orchestrator (runs every 15 minutes)"
echo "   3. Security Scanning (runs daily at 2 AM UTC)"
echo "   4. Circuit Breaker Monitor (runs hourly)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "STEP 1: Enable Scheduled Workflows"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Scheduled workflows (cron-based) are automatically disabled in GitHub"
echo "after 60 days of repository inactivity."
echo ""
echo "To enable them:"
echo "1. Go to: https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/actions"
echo "2. Look for workflows marked as 'Disabled' or with a pause icon"
echo "3. Click on each scheduled workflow and click 'Enable workflow'"
echo ""
echo "Workflows to enable:"
echo "   • Continuous Health Monitoring (health-monitor.yml)"
echo "   • Workflow Orchestrator (workflow-orchestrator.yml)"
echo "   • Security & Dependency Scanning (security.yml)"
echo "   • Circuit Breaker Monitor (circuit-breaker-monitor.yml)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "STEP 2: Set Up Required Repository Variables"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "The orchestration system needs these GitHub repository variables:"
echo ""
echo "Run these commands (requires GH_PAT or GITHUB_TOKEN):"
echo ""
cat << 'EOF'
# Health Check Tracking
gh variable set HEALTH_CHECK_HISTORY --body "[]"
gh variable set HEALTH_CHECK_CONSECUTIVE_DEGRADED --body "0"
gh variable set LAST_HEALTH_STATUS --body "unknown"

# Circuit Breaker State
gh variable set CIRCUIT_BREAKER_STATE --body "closed"
gh variable set CIRCUIT_BREAKER_FAILURES --body "0"
gh variable set CIRCUIT_BREAKER_LAST_FAILURE --body ""

# Deployment Tracking
gh variable set LAST_SUCCESSFUL_DEPLOYMENT --body ""
gh variable set CURRENT_DEPLOYED_DIGEST --body ""

# Orchestration Session Tracking
gh variable set ORCHESTRATION_SESSION_ID --body ""
gh variable set ORCHESTRATION_START_TIME --body ""
gh variable set ORCHESTRATION_ACTION --body ""

# Recovery Tracking
gh variable set LAST_RECOVERY_ATTEMPT --body ""
gh variable set RECOVERY_ATTEMPTS_COUNT --body "0"
EOF
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "STEP 3: Verify Required Secrets"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Required secrets (should already be set):"
echo "   • TS_OAUTH_CLIENT_ID - Tailscale OAuth client ID"
echo "   • TS_OAUTH_SECRET - Tailscale OAuth secret"
echo "   • GH_PAT - GitHub Personal Access Token (for workflow orchestration)"
echo ""
echo "To check which secrets are set:"
echo "   gh secret list"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "STEP 4: Manual Test Run"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "After enabling workflows, test them manually:"
echo ""
echo "1. Test Health Monitor:"
echo "   gh workflow run health-monitor.yml"
echo ""
echo "2. Test Workflow Orchestrator:"
echo "   gh workflow run workflow-orchestrator.yml -f orchestration_action=status-check"
echo ""
echo "3. Test Security Scan:"
echo "   gh workflow run security.yml"
echo ""
echo "4. Check all workflow runs:"
echo "   gh run list --limit 20"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "STEP 5: Monitor Orchestration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Once enabled, the orchestration system will:"
echo ""
echo "• Every 5 minutes: Health Monitor checks service health"
echo "  - If unhealthy for 3+ checks → triggers Recovery workflow"
echo "  - Records health history in GitHub variables"
echo ""
echo "• Every 15 minutes: Workflow Orchestrator validates"
echo "  - Workflow dependency states"
echo "  - System consistency"
echo "  - Workflow health metrics"
echo ""
echo "• Every hour: Circuit Breaker Monitor"
echo "  - Checks deployment failure patterns"
echo "  - Opens circuit if failure threshold exceeded"
echo ""
echo "• Daily at 2 AM UTC: Security scanning"
echo "  - Dependency vulnerabilities"
echo "  - Code security issues"
echo "  - Container scanning"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "ORCHESTRATION FLOW DIAGRAM"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
cat << 'EOF'
┌─────────────────────────────────────────────────────────┐
│                   MAIN DEPLOYMENT FLOW                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Code Push → CI (test/build)                           │
│       │                                                 │
│       ↓                                                 │
│  Integration Tests                                      │
│       │                                                 │
│       ↓                                                 │
│  Deploy to Production                                   │
│       │                                                 │
│       ↓                                                 │
│  Health Verification                                    │
│                                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              ORCHESTRATION & MONITORING                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────┐      Every 5 minutes              │
│  │ Health Monitor  │──────────────────┐                │
│  └─────────────────┘                  │                │
│         │                             │                │
│         │ Unhealthy (3+ checks)       │                │
│         ↓                             │                │
│  ┌─────────────────┐                 │                │
│  │    Recovery     │                 │                │
│  │   Workflow      │                 │                │
│  └─────────────────┘                 │                │
│         │                             │                │
│         ├─> Container Restart         │                │
│         ├─> Log Analysis              │                │
│         └─> Redeploy if needed        │                │
│                                       │                │
│  ┌─────────────────────┐     Every 15 minutes          │
│  │Workflow Orchestrator│<──────────────┘                │
│  └─────────────────────┘                               │
│         │                                              │
│         ├─> Validates workflow dependencies            │
│         ├─> Checks system consistency                  │
│         └─> Reports workflow health                    │
│                                                         │
│  ┌───────────────────┐       Every hour                │
│  │Circuit Breaker    │                                 │
│  │   Monitor         │                                 │
│  └───────────────────┘                                 │
│         │                                              │
│         └─> Blocks deploys if too many failures        │
│                                                         │
│  ┌───────────────────┐       Daily 2 AM UTC            │
│  │Security Scanner   │                                 │
│  └───────────────────┘                                 │
│         │                                              │
│         ├─> Dependency vulnerabilities                 │
│         ├─> Code security issues                       │
│         └─> Container scanning                         │
│                                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                 MANUAL INTERVENTIONS                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  • Manual Rollback (via workflow dispatch)             │
│  • Force Recovery (override health checks)              │
│  • Override Circuit Breaker (emergency only)            │
│  • Bypass Deployment Gating (with reason)              │
│                                                         │
└─────────────────────────────────────────────────────────┘
EOF
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "QUICK COMMANDS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "# Check workflow status"
echo "gh run list --limit 10"
echo ""
echo "# View specific workflow runs"
echo "gh run list --workflow=health-monitor.yml --limit 5"
echo ""
echo "# Watch a running workflow"
echo "gh run watch"
echo ""
echo "# View workflow logs"
echo "gh run view <run-id> --log"
echo ""
echo "# Check repository variables"
echo "gh variable list"
echo ""
echo "# Trigger manual workflows"
echo "gh workflow run health-monitor.yml"
echo "gh workflow run workflow-orchestrator.yml -f orchestration_action=status-check"
echo "gh workflow run recovery.yml -f health_status=degraded -f recovery_reason=manually_forced"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📚 For more details, see:"
echo "   • docs/CI_CD.md - Complete CI/CD documentation"
echo "   • docs/RECOVERY_SYSTEM.md - Recovery system guide"
echo "   • .github/workflows/README.md - Workflow documentation"
echo ""
echo "✅ Once these steps are complete, your full orchestration system will be active!"
echo ""
