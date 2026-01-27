# Orchestration System Activation Checklist

This checklist will help you activate the complete orchestration system for Tailpaste.

## Current Status

✅ **Main Pipeline Working** - CI → Integration Tests → Deploy
❓ **Orchestration Components** - Need to be activated

---

## Activation Steps

### Step 1: Set Up Repository Variables

Run the initialization script to create all required GitHub variables:

```bash
chmod +x scripts/init-orchestration-variables.sh
./scripts/init-orchestration-variables.sh
```

Or manually set them using the commands in the script.

**Required Variables:**
- [ ] Health check tracking (HEALTH_CHECK_HISTORY, LAST_HEALTH_STATUS, etc.)
- [ ] Circuit breaker state (CIRCUIT_BREAKER_STATE, CIRCUIT_BREAKER_FAILURES, etc.)
- [ ] Deployment tracking (CURRENT_DEPLOYED_DIGEST, LAST_SUCCESSFUL_DEPLOYMENT, etc.)
- [ ] Orchestration session (ORCHESTRATION_SESSION_ID, ORCHESTRATION_STATUS, etc.)
- [ ] Recovery system (LAST_RECOVERY_ATTEMPT, RECOVERY_ATTEMPTS_COUNT, etc.)

**Verify:**
```bash
gh variable list
```

---

### Step 2: Enable Scheduled Workflows in GitHub

GitHub disables scheduled (cron-based) workflows automatically. You need to enable them:

1. Go to: https://github.com/YOUR_USERNAME/Tailpaste/actions
2. Look for workflows with schedules:
   - [ ] **Continuous Health Monitoring** (runs every 5 minutes)
   - [ ] **Workflow Orchestrator** (runs every 15 minutes)
   - [ ] **Security & Dependency Scanning** (runs daily at 2 AM UTC)
   - [ ] **Circuit Breaker Monitor** (runs hourly)
   - [ ] **Health Check** (runs hourly - backup health check)

3. For each disabled workflow:
   - Click on the workflow name
   - Click the "Enable workflow" button
   - Confirm enablement

---

### Step 3: Verify Required Secrets

Check that all necessary secrets are configured:

```bash
gh secret list
```

**Required Secrets:**
- [ ] `TS_OAUTH_CLIENT_ID` - Tailscale OAuth client ID
- [ ] `TS_OAUTH_SECRET` - Tailscale OAuth secret  
- [ ] `GH_PAT` - GitHub Personal Access Token (for workflow orchestration)

**Optional Secrets:**
- [ ] `SLACK_WEBHOOK_URL` - For Slack notifications

---

### Step 4: Test Scheduled Workflows Manually

Before waiting for cron schedules, test each workflow manually:

```bash
# Test Health Monitor
gh workflow run health-monitor.yml
echo "Waiting for workflow to start..."
sleep 5
gh run list --workflow=health-monitor.yml --limit 1

# Test Workflow Orchestrator
gh workflow run workflow-orchestrator.yml -f orchestration_action=status-check
sleep 5
gh run list --workflow=workflow-orchestrator.yml --limit 1

# Test Security Scanner
gh workflow run security.yml
sleep 5
gh run list --workflow=security.yml --limit 1

# Test Circuit Breaker Monitor
gh workflow run circuit-breaker-monitor.yml
sleep 5
gh run list --workflow=circuit-breaker-monitor.yml --limit 1
```

**Check Results:**
```bash
# Watch the most recent workflow run
gh run watch

# Or view specific run logs
gh run view <RUN_ID> --log
```

---

### Step 5: Verify Orchestration Integration

Make a test commit to verify the complete flow:

```bash
# Make a small change (e.g., update README)
echo "# Test orchestration - $(date)" >> TEST_ORCHESTRATION.md
git add TEST_ORCHESTRATION.md
git commit -m "test: verify orchestration system"
git push origin main
```

**Monitor the Flow:**
```bash
# Watch all workflows
gh run list --limit 20

# Expected flow:
# 1. CI workflow starts (triggered by push)
# 2. Integration Tests start (after CI succeeds)
# 3. Deploy workflow starts (after Integration Tests succeed)
# 4. Health Monitor runs periodically (every 5 min)
# 5. Workflow Orchestrator validates state (every 15 min)
```

---

### Step 6: Monitor for First 24 Hours

Once activated, monitor the system for the first 24 hours:

**Check Health Monitoring:**
```bash
# View health monitor runs
gh run list --workflow=health-monitor.yml --limit 10

# Check health history variable
gh variable get HEALTH_CHECK_HISTORY
gh variable get LAST_HEALTH_STATUS
```

**Check Orchestration:**
```bash
# View orchestrator runs
gh run list --workflow=workflow-orchestrator.yml --limit 10

# Check orchestration variables
gh variable get ORCHESTRATION_SESSION_ID
gh variable get ORCHESTRATION_STATUS
```

**Check Circuit Breaker:**
```bash
# View circuit breaker runs
gh run list --workflow=circuit-breaker-monitor.yml --limit 10

# Check circuit breaker state
gh variable get CIRCUIT_BREAKER_STATE
gh variable get CIRCUIT_BREAKER_FAILURES
```

---

## What Happens After Activation

### Health Monitoring (Every 5 Minutes)
- Checks service availability
- Records health history
- Triggers recovery if unhealthy for 3+ consecutive checks
- Updates `HEALTH_CHECK_HISTORY` variable

### Workflow Orchestration (Every 15 Minutes)
- Validates workflow dependencies
- Checks system consistency
- Reports workflow health metrics
- Identifies stuck or failing workflows

### Circuit Breaker (Every Hour)
- Monitors deployment failure patterns
- Opens circuit after threshold failures
- Prevents deployments when circuit is open
- Auto-recovers after cooldown period

### Security Scanning (Daily at 2 AM UTC)
- Scans dependencies for vulnerabilities
- Performs code security analysis
- Scans containers with Trivy
- Uploads security reports

---

## Troubleshooting

### Workflows Not Running on Schedule

**Problem:** Scheduled workflows don't run automatically.

**Solution:**
1. Check if workflows are enabled in GitHub Actions
2. Make at least one commit to trigger repository activity
3. Verify runner labels match: `tailpaste-runners`
4. Check runner availability: Ensure self-hosted runners are online

### Permission Errors

**Problem:** Workflows fail with permission errors.

**Solution:**
1. Verify `GH_PAT` secret has `repo` and `workflow` scopes
2. Check workflow permissions in YAML (should have `actions: write`)
3. Ensure repository allows workflow access to variables

### Health Monitor Always Reports Unknown

**Problem:** Health status stays "unknown".

**Solution:**
1. Check Tailscale connectivity from runner
2. Verify service is actually running: `docker ps`
3. Check service URL is correct in health check script
4. Review health monitor logs: `gh run view <RUN_ID> --log`

### Variables Not Updating

**Problem:** GitHub variables don't update during workflow runs.

**Solution:**
1. Verify `GH_PAT` has correct permissions
2. Check that workflows have `actions: write` permission
3. Ensure variable names match exactly (case-sensitive)
4. Try setting one variable manually to test: `gh variable set TEST_VAR --body "test"`

---

## Success Criteria

You'll know the orchestration system is fully working when:

- [ ] Health monitor runs every 5 minutes automatically
- [ ] Workflow orchestrator runs every 15 minutes automatically
- [ ] Security scans run daily
- [ ] Health status variables update after each check
- [ ] Circuit breaker monitors deployment patterns
- [ ] Recovery workflow can be triggered by health failures
- [ ] Manual rollback works via workflow dispatch
- [ ] All workflow runs show green checkmarks in Actions tab

---

## Quick Reference Commands

```bash
# View all recent workflow runs
gh run list --limit 20

# View specific workflow runs
gh run list --workflow=health-monitor.yml --limit 5

# Watch a running workflow
gh run watch

# View workflow logs
gh run view <RUN_ID> --log

# Check all variables
gh variable list

# Get specific variable
gh variable get HEALTH_CHECK_HISTORY

# Manually trigger workflows
gh workflow run health-monitor.yml
gh workflow run workflow-orchestrator.yml -f orchestration_action=status-check

# Enable all workflows at once (if you have jq installed)
gh workflow list --json path,state | jq -r '.[] | select(.state=="disabled") | .path' | xargs -I {} gh workflow enable -f {}
```

---

## Documentation References

- **Complete CI/CD Guide:** [docs/CI_CD.md](../docs/CI_CD.md)
- **Recovery System:** [docs/RECOVERY_SYSTEM.md](../docs/RECOVERY_SYSTEM.md)
- **Workflow Documentation:** [.github/workflows/README.md](../.github/workflows/README.md)
- **Script Documentation:** [.github/scripts/README.md](../.github/scripts/README.md)

---

## Support

If you encounter issues:

1. Check workflow run logs in GitHub Actions
2. Review the documentation files listed above
3. Check runner logs if using self-hosted runners
4. Verify all secrets and variables are set correctly
5. Test individual components in isolation

---

**Last Updated:** January 25, 2026
