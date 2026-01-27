# Enhanced Debugging Integration Guide

This guide explains how to integrate the enhanced debugging system into your Tailpaste CI/CD workflows.

## 🎯 What Was Added

### New Debug Scripts
- **`debug-helpers.sh`** - Core library with logging, inspection, and diagnostics functions
- **`diagnose-workflow.sh`** - Standalone diagnostic tool for troubleshooting
- **`enhanced-health-monitor.sh`** - Health checks with integrated debugging
- **`health-check-debug.sh`** - Wrapper script for comprehensive debugging workflows
- **`health-monitor-enhanced.yml`** - Updated workflow with debug capabilities

### Documentation
- **`README.md`** - Complete function reference and examples
- **`QUICK_START.md`** - Getting started guide with common scenarios
- **`INTEGRATION.md`** - This file

## 🔧 Immediate Usage

### For Local Testing

```bash
# 1. Navigate to repo
cd /Users/michael/Tailpaste

# 2. Run diagnostics
.github/scripts/debug/diagnose-workflow.sh full

# 3. Run health checks with debugging
.github/scripts/debug/health-check-debug.sh -v

# 4. Collect all artifacts
.github/scripts/debug/health-check-debug.sh -vv -d -s ./artifacts
```

### For GitHub Actions

#### Option A: Use Enhanced Workflow

The new `health-monitor-enhanced.yml` includes built-in debugging:

```bash
# Enable it by renaming or creating a workflow dispatcher
cp .github/workflows/health-monitor-enhanced.yml .github/workflows/health-monitor.yml
```

#### Option B: Add Debugging to Existing Workflow

Add these steps to your existing health-monitor workflow:

```yaml
# Early in workflow
- name: Run pre-check diagnostics
  if: ${{ inputs.debug_mode == true }}
  continue-on-error: true
  run: |
    chmod +x .github/scripts/debug/diagnose-workflow.sh
    .github/scripts/debug/diagnose-workflow.sh full
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

# When running health checks
- name: Execute health checks with debugging
  id: health_checks
  run: |
    chmod +x .github/scripts/debug/health-check-debug.sh
    if [[ "${{ inputs.debug_mode }}" == "true" ]]; then
      .github/scripts/debug/health-check-debug.sh -v -d
    else
      .github/scripts/debug/health-check-debug.sh
    fi
  continue-on-error: true
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

# After checks complete
- name: Upload debug artifacts
  if: ${{ failure() && always() }}
  uses: actions/upload-artifact@v4
  with:
    name: health-monitor-debug
    path: /tmp/health-check-artifacts
    retention-days: 7
```

## 🔌 Integration Points

### 1. Import in Shell Scripts

```bash
#!/bin/bash
set -euo pipefail

# Import debug library
source ./.github/scripts/debug/debug-helpers.sh

# Set context
export WORKFLOW_CONTEXT="MyScript"

# Use logging
log_info "Starting process"
log_debug "Debug details"

# Inspect environment
inspect_github_env
inspect_tools

# If something fails
if ! some_command; then
    log_error "Command failed"
    diagnose_variable_failure "MY_VAR" "get"
    exit 1
fi

log_info "Process complete"
```

### 2. Wrap Existing Scripts

Instead of calling scripts directly:

```bash
# Old way
.github/scripts/health-check/execute-health-checks.sh

# New way - with debugging
chmod +x .github/scripts/debug/health-check-debug.sh
.github/scripts/debug/health-check-debug.sh -v
```

### 3. Add Debug Info to Artifacts

In GitHub Actions:

```yaml
- name: Collect debug info
  if: always()
  run: |
    mkdir -p debug-artifacts
    # Copy logs
    cp /tmp/workflow-debug.log debug-artifacts/ 2>/dev/null || true
    cp /tmp/health-check-debug.log debug-artifacts/ 2>/dev/null || true
    # Run diagnostics
    .github/scripts/debug/diagnose-workflow.sh report debug-artifacts/workflow-diagnostics.txt
```

## 📊 Configuration Options

### Environment Variables

```bash
# Set debug verbosity (0-5)
export WORKFLOW_DEBUG_LEVEL=4  # DEBUG
export WORKFLOW_DEBUG_LEVEL=5  # TRACE

# Custom log file
export DEBUG_LOG_FILE=/tmp/custom-debug.log

# Service URL (for health checks)
export TAILPASTE_URL=http://localhost:8080
```

### Workflow Inputs

The enhanced workflow supports:

```yaml
# Enable debug mode
debug_mode: true

# Force recovery
force_recovery: false

# Skip recovery
skip_recovery: false
```

## 🚨 Troubleshooting Permission Issues

### Issue: `HTTP 403: Resource not accessible by integration`

**Root Cause:** Workflow lacks variable write permissions

**Fix 1: Update Workflow Permissions**
```yaml
permissions:
  contents: read
  actions: write  # ← Add this line
```

**Fix 2: Check Repository Settings**
1. Go to Settings → Actions → General
2. Under "Workflow permissions" select "Read and write permissions"
3. Check "Allow GitHub Actions to create and approve pull requests"

**Diagnose:**
```bash
.github/scripts/debug/diagnose-workflow.sh variable TEST_VAR
```

## 📈 Performance Considerations

### Log Retention
```yaml
# In workflow
- name: Upload artifacts
  uses: actions/upload-artifact@v4
  with:
    retention-days: 7  # Delete after 7 days
```

### Debug Levels for Performance
```bash
# Production (minimal overhead)
WORKFLOW_DEBUG_LEVEL=1  # Errors only

# Development (balanced)
WORKFLOW_DEBUG_LEVEL=3  # Default (INFO)

# Heavy debugging (impacts performance)
WORKFLOW_DEBUG_LEVEL=5  # Trace everything
```

## 🎯 Recommended Setup

### For Development

```bash
# 1. Test locally with full debugging
.github/scripts/debug/health-check-debug.sh -vv -d -t -s ./artifacts

# 2. Review artifacts
cat ./artifacts/logs/health-check.log
cat ./artifacts/diagnostics/workflow-diagnostics.txt
```

### For CI/CD

```yaml
# In your workflow
- name: Health checks with selective debugging
  run: |
    chmod +x .github/scripts/debug/health-check-debug.sh
    
    # Debug mode on only on failure (via workflow_dispatch)
    if [[ "${{ inputs.debug_mode }}" == "true" ]]; then
      .github/scripts/debug/health-check-debug.sh -vv -d -s /tmp/artifacts
    else
      .github/scripts/debug/health-check-debug.sh
    fi
  continue-on-error: true

- name: Upload artifacts on failure
  if: ${{ failure() }}
  uses: actions/upload-artifact@v4
  with:
    name: debug-artifacts
    path: /tmp/artifacts
    retention-days: 7
```

## 🔗 Connecting to Existing Systems

### Health Check Scripts

The debugging system wraps existing health check scripts:
- `init-monitoring-session.sh`
- `execute-health-checks.sh`
- `record-health-results.sh`

No modifications needed - they work alongside debugging tools.

### Recovery Workflow

The enhanced workflow can trigger recovery with additional context:

```yaml
- name: Trigger recovery with debug info
  if: ${{ failure() }}
  run: |
    gh workflow run recovery.yml \
      --field health_status="unhealthy" \
      --field recovery_reason="health_check_failed" \
      --field debug_artifacts_available="true"
```

## 📚 Documentation Hierarchy

```
.github/scripts/debug/
├── README.md              ← Function reference
├── QUICK_START.md         ← Getting started
├── INTEGRATION.md         ← This file
└── Scripts
    ├── debug-helpers.sh   ← Core library
    ├── diagnose-workflow.sh
    ├── enhanced-health-monitor.sh
    └── health-check-debug.sh

.github/workflows/
└── health-monitor-enhanced.yml  ← Example workflow
```

## ✅ Verification Checklist

After integration:

- [ ] All debug scripts are executable (`chmod +x`)
- [ ] `debug-helpers.sh` is sourced before using logging functions
- [ ] `WORKFLOW_CONTEXT` is set appropriately
- [ ] Workflow has proper permissions (actions: write)
- [ ] GitHub CLI is installed and authenticated
- [ ] Debug artifacts are captured on failure
- [ ] Log retention policies are configured
- [ ] Team is familiar with quick-start guide

## 🚀 Next Steps

1. **Review** `QUICK_START.md` for common scenarios
2. **Test locally** using health check debug script
3. **Integrate** into your workflow gradually
4. **Monitor** first runs to verify output
5. **Adjust** debug levels based on needs
6. **Document** any custom additions

## 🤝 Support

For issues:
1. Run diagnostics: `.github/scripts/debug/diagnose-workflow.sh full`
2. Check logs: `cat /tmp/workflow-debug.log`
3. Review artifacts: `cat debug-artifacts/diagnostics/*.txt`
4. Consult main docs: `docs/CI_CD.md`

## 📝 Maintenance

### Keep Scripts Updated
When modifying health check workflow:
1. Update both `health-monitor.yml` and `health-monitor-enhanced.yml`
2. Test with debug tools before deploying
3. Document any new logging points

### Archive Old Artifacts
Regularly clean up:
```bash
# Remove artifacts older than 30 days
find /tmp -name "health-check-artifacts" -mtime +30 -exec rm -rf {} \;
```

---

**Ready to enhance your debugging?** Start with the QUICK_START.md guide!

