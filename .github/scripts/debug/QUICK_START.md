# Enhanced Debugging Quick Start Guide

## 🚀 Getting Started

### 1. Basic Health Check with Debugging

Run health checks with verbose output:

```bash
cd /Users/michael/Tailpaste
chmod +x .github/scripts/debug/health-check-debug.sh
.github/scripts/debug/health-check-debug.sh -v
```

### 2. Diagnose Current Issues

Get comprehensive diagnostics:

```bash
chmod +x .github/scripts/debug/diagnose-workflow.sh
.github/scripts/debug/diagnose-workflow.sh full
```

### 3. Collect Debug Artifacts

Run checks and save all debug information:

```bash
.github/scripts/debug/health-check-debug.sh -vv -d -t -s ./debug-artifacts
ls -la ./debug-artifacts/
```

## 📋 Common Scenarios

### Scenario 1: GitHub Variable Permission Error

**Problem:** Workflow shows `HTTP 403: Resource not accessible by integration`

**Solution:**

1. **Run diagnostics:**
   ```bash
   .github/scripts/debug/diagnose-workflow.sh variable LAST_HEALTH_CHECK_START
   ```

2. **Check workflow permissions:** Verify `.github/workflows/health-monitor.yml` has:
   ```yaml
   permissions:
     actions: write
   ```

3. **Check repository settings:**
   - Go to Settings → Actions → General
   - Verify "Allow GitHub Actions to create and approve pull requests"
   - Check "Workflow permissions" is set to "Read and write permissions"

### Scenario 2: Service Connection Failures

**Problem:** Health checks can't reach the service

**Solution:**

1. **Run with diagnostics:**
   ```bash
   .github/scripts/debug/health-check-debug.sh -d -v
   ```

2. **Check service status:**
   ```bash
   curl -v http://tailpaste:8080/
   ```

3. **Inspect Tailscale:**
   ```bash
   tailscale status
   tailscale ip -4
   ```

### Scenario 3: Debug Failed Workflow Run

**Problem:** Workflow failed, need to understand why

**Solution:**

1. **Manual diagnostics run (locally or in CI):**
   ```bash
   # Full trace with all details
   WORKFLOW_DEBUG_LEVEL=5 .github/scripts/debug/diagnose-workflow.sh report /tmp/report.txt
   cat /tmp/report.txt
   ```

2. **Check workflow artifacts:** In GitHub Actions UI, download debug artifacts from failed run

3. **Review logs:** Check `/tmp/workflow-debug.log` for detailed execution trace

## 🔧 Debug Functions Reference

### Logging (Use in shell scripts)

```bash
#!/bin/bash
source .github/scripts/debug/debug-helpers.sh

log_error "Something went wrong"      # Red, always shown
log_warn "Warning message"            # Yellow, shown at level 2+
log_info "Info message"               # Green, shown at level 3+ (default)
log_debug "Debug details"             # Blue, shown at level 4+
log_trace "Trace execution"           # Cyan, shown at level 5
```

### Inspection (Check system state)

```bash
# Check GitHub Actions environment
inspect_github_env

# List available tools
inspect_tools

# Verify GitHub CLI setup
inspect_gh_config

# Check workflow permissions
inspect_permissions

# List repository variables
inspect_variables

# Review step outputs
inspect_step_outputs
```

### Diagnosis (Troubleshoot issues)

```bash
# Diagnose variable operation failure
diagnose_variable_failure "MY_VAR" "set"

# Generate comprehensive report
generate_debug_report /tmp/my-report.txt
```

## 📊 Understanding Debug Output

### Log Format
```
[2026-01-27T09:37:00.486Z] [DEBUG] [function_name] Processing item 1/100
  ↑                          ↑       ↑               ↑
  Timestamp (UTC)            Level   Context         Message
```

### Artifact Files
```
debug-artifacts/
├── logs/
│   └── health-check.log          # All debug output
├── outputs/
│   ├── github-output.txt         # Step outputs
│   └── github-env.txt            # Environment variables
├── diagnostics/
│   ├── workflow-diagnostics.txt  # Detailed system info
│   └── debug-report.txt          # Comprehensive report
└── MANIFEST.txt                  # File listing
```

## 🎯 Workflow Integration

### Add to health-monitor.yml

```yaml
- name: Run health checks with debugging
  run: |
    chmod +x .github/scripts/debug/health-check-debug.sh
    .github/scripts/debug/health-check-debug.sh -v -d
  env:
    WORKFLOW_DEBUG_LEVEL: 4  # DEBUG level

- name: Upload debug artifacts
  if: ${{ failure() }}
  uses: actions/upload-artifact@v4
  with:
    name: health-check-debug-${{ github.run_id }}
    path: /tmp/health-check-artifacts
    retention-days: 7
```

## 🐛 Troubleshooting Tips

1. **Enable maximum verbosity:**
   ```bash
   WORKFLOW_DEBUG_LEVEL=5 ./script.sh
   ```

2. **Save logs to file:**
   ```bash
   DEBUG_LOG_FILE=/tmp/my-log.txt ./script.sh
   ```

3. **Run with execution tracing:**
   ```bash
   bash -x script.sh 2>&1 | tee /tmp/trace.log
   ```

4. **Check tool versions:**
   ```bash
   .github/scripts/debug/diagnose-workflow.sh tools
   ```

5. **Inspect environment:**
   ```bash
   .github/scripts/debug/diagnose-workflow.sh environment
   ```

## 📈 Performance Tips

- **Faster diagnostics:** Run targeted diagnose commands instead of `full`
- **Reduce log noise:** Use appropriate debug level (3 for default, 1 for errors only)
- **Archive artifacts:** Set retention days to avoid storage bloat
- **Parallel checks:** Run independent health checks in parallel when possible

## 🔍 Advanced Usage

### Custom Logging Context

```bash
export WORKFLOW_CONTEXT="my-custom-context"
log_info "Message with custom context"
# Output: [timestamp] [INFO] [my-custom-context] Message with custom context
unset WORKFLOW_CONTEXT
```

### Function Execution Tracing

```bash
trace_function "my_function"
# ... do work ...
trace_function_exit  # Automatically calculates duration
```

### Generate Custom Report

```bash
generate_debug_report /tmp/custom-report.txt
# Creates comprehensive report with environment info
```

## 📚 More Information

- [Debug Helpers Reference](./README.md)
- [Health Check Scripts](../health-check/)
- [Workflow CI/CD Documentation](../../../docs/CI_CD.md)
- [GitHub Actions Debugging](https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows)

## ❓ FAQ

**Q: Why are my variables showing as `[REDACTED]`?**
A: The tool automatically masks sensitive variables (secrets, tokens, passwords) in output

**Q: Can I use debug helpers in GitHub Actions directly?**
A: Yes! Source them in your workflow steps:
```bash
source .github/scripts/debug/debug-helpers.sh
log_info "Running in GitHub Actions"
```

**Q: How do I change the debug level?**
A: Set environment variable:
```bash
export WORKFLOW_DEBUG_LEVEL=4  # DEBUG level
export WORKFLOW_DEBUG_LEVEL=5  # TRACE level
```

**Q: Where are logs stored?**
A: Default is `/tmp/workflow-debug.log`. Change with:
```bash
export DEBUG_LOG_FILE=/tmp/my-custom.log
```

## 💡 Pro Tips

1. **Always run diagnostics first** when troubleshooting
2. **Save artifacts in CI** for later analysis
3. **Use context appropriately** to track where logs come from
4. **Set appropriate debug level** to reduce noise
5. **Check tool availability** early in workflows

---

**Happy Debugging! 🚀**

For issues or improvements, refer to the main documentation or contact the development team.

