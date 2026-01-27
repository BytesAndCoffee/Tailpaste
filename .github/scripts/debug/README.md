# Enhanced Debugging Tools for Tailpaste

This directory contains comprehensive debugging utilities for troubleshooting GitHub Actions workflows and health monitoring in Tailpaste.

## 📚 Scripts Overview

### 1. `debug-helpers.sh`
Core debugging library providing:
- **Structured Logging**: Timestamp-based, context-aware logging with multiple levels (ERROR, WARN, INFO, DEBUG, TRACE)
- **State Inspection**: Functions to examine GitHub Actions environment, tools, CLI configuration, permissions, variables, and step outputs
- **Error Diagnostics**: Specialized functions for diagnosing failures
- **Execution Tracing**: Function-level tracing with performance metrics
- **Debug Reporting**: Generate comprehensive diagnostic reports

**Import in your scripts:**
```bash
source .github/scripts/debug/debug-helpers.sh

# Use logging functions
log_info "This is an info message"
log_debug "Detailed debug info"
log_error "An error occurred"

# Inspect environment
inspect_github_env
inspect_tools
inspect_gh_config
```

**Logging Functions:**
- `log_error()` - Log errors (level 1)
- `log_warn()` - Log warnings (level 2)
- `log_info()` - Log info (level 3, default)
- `log_debug()` - Log debug details (level 4)
- `log_trace()` - Log trace information (level 5)

**Inspection Functions:**
- `inspect_github_env()` - Check GitHub Actions environment variables
- `inspect_tools()` - List available tools and versions
- `inspect_gh_config()` - Verify GitHub CLI setup
- `inspect_variables()` - List and check repository variables
- `inspect_permissions()` - Test workflow permissions
- `inspect_step_outputs()` - Check GitHub output files
- `diagnose_variable_failure()` - Debug variable operation failures

### 2. `diagnose-workflow.sh`
Comprehensive workflow diagnostics tool.

**Usage:**
```bash
# Run full diagnostic suite
.github/scripts/debug/diagnose-workflow.sh full

# Diagnose specific issues
.github/scripts/debug/diagnose-workflow.sh variable SOME_VAR
.github/scripts/debug/diagnose-workflow.sh permissions
.github/scripts/debug/diagnose-workflow.sh github-cli

# Generate detailed report
.github/scripts/debug/diagnose-workflow.sh report /tmp/diagnostic-report.txt
```

**Output:**
- Environment information (repository, workflow, runner details)
- Tool availability and versions
- GitHub CLI status and authentication
- Token status
- Environment variable dump
- Output file inspection

### 3. `enhanced-health-monitor.sh`
Enhanced health check with integrated debugging.

**Usage:**
```bash
# Basic health checks
.github/scripts/debug/enhanced-health-monitor.sh

# With debug output
.github/scripts/debug/enhanced-health-monitor.sh --debug

# With tracing
.github/scripts/debug/enhanced-health-monitor.sh --trace

# With full diagnostics before checks
.github/scripts/debug/enhanced-health-monitor.sh --diagnose
```

**Features:**
- Service availability check
- Functionality verification
- Tailscale connectivity check
- Database status check
- Automatic debug log generation

### 4. `health-check-debug.sh`
Wrapper script that orchestrates all debugging features for health checks.

**Usage:**
```bash
# Verbose health checks
.github/scripts/debug/health-check-debug.sh -v

# Very verbose with tracing
.github/scripts/debug/health-check-debug.sh -vv -t

# With diagnostics and artifact collection
.github/scripts/debug/health-check-debug.sh -d -s /tmp/artifacts

# Full diagnostic package
.github/scripts/debug/health-check-debug.sh -vv -d -t -s ./debug-artifacts
```

**Options:**
- `-v, --verbose` - Enable DEBUG level logging
- `-vv, --very-verbose` - Enable TRACE level logging
- `-d, --diagnose` - Run pre-check diagnostics
- `-t, --trace` - Enable execution tracing
- `-s, --save-artifacts [DIR]` - Save debug artifacts to directory
- `-h, --help` - Show help message

**Artifact Collection:**
When using `-s` flag, automatically collects:
- Health check logs
- GitHub output/environment files
- Workflow diagnostics
- Debug reports
- Execution manifests

## 🔧 Integration Examples

### In GitHub Actions Workflow

Add debugging to your health monitoring workflow:

```yaml
- name: Run health checks with debugging
  run: |
    chmod +x .github/scripts/debug/health-check-debug.sh
    .github/scripts/debug/health-check-debug.sh -v -d -s /tmp/artifacts
  continue-on-error: true

- name: Upload debug artifacts
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: health-check-debug-artifacts
    path: /tmp/artifacts
    retention-days: 7
```

### In Shell Scripts

```bash
#!/bin/bash
set -euo pipefail

# Import debugging helpers
source .github/scripts/debug/debug-helpers.sh

export WORKFLOW_CONTEXT="MyScript"

log_info "Starting my process"
log_debug "Debug details here"

# Do work...

if some_operation_fails; then
    log_error "Operation failed"
    diagnose_variable_failure "MY_VAR" "set"
    exit 1
fi

log_info "Process completed successfully"
```

## 📊 Debug Levels

Control verbosity using `WORKFLOW_DEBUG_LEVEL`:

```bash
export WORKFLOW_DEBUG_LEVEL=5  # Maximum verbosity (TRACE)
# or
export WORKFLOW_DEBUG_LEVEL=3  # Default (INFO)
# or
export WORKFLOW_DEBUG_LEVEL=1  # Errors only
```

| Level | Name  | When to Use |
|-------|-------|-------------|
| 1     | ERROR | Production - only show errors |
| 2     | WARN  | Production - show errors and warnings |
| 3     | INFO  | Default - balanced information |
| 4     | DEBUG | Development - detailed diagnostics |
| 5     | TRACE | Deep debugging - trace execution flow |

## 🐛 Troubleshooting Common Issues

### GitHub Variable Permission Errors (HTTP 403)

**Error:**
```
failed to set variable "SOME_VAR": HTTP 403: Resource not accessible by integration
```

**Diagnose:**
```bash
.github/scripts/debug/diagnose-workflow.sh variable SOME_VAR set
```

**Solutions:**
1. Check workflow file permissions:
   ```yaml
   permissions:
     actions: write  # or
     vars: write
   ```

2. Verify GitHub CLI authentication:
   ```bash
   .github/scripts/debug/diagnose-workflow.sh github-cli
   ```

3. Check repository settings for workflow permissions

### Missing Scripts or Tools

**Diagnose:**
```bash
.github/scripts/debug/diagnose-workflow.sh tools
```

**Output shows missing tools** → Install via workflow setup steps

### Environment Variable Issues

**Diagnose:**
```bash
.github/scripts/debug/diagnose-workflow.sh environment
```

**Shows missing GITHUB_ACTIONS variable** → Running outside GitHub Actions

## 📈 Performance Metrics

All logging includes timing information:
```
[2026-01-27T09:37:00.486Z] [TRACE] [function_name] → Entering function: my_operation
[2026-01-27T09:37:00.487Z] [DEBUG] [function_name] Processing item 1/100
[2026-01-27T09:37:00.588Z] [TRACE] [function_name] ← Exiting function: my_operation (102ms)
```

Timestamps are in UTC with millisecond precision for easy correlation with logs.

## 📝 Log Files

Debug logs are automatically saved to:
- **Default**: `/tmp/workflow-debug.log`
- **Custom**: Set `DEBUG_LOG_FILE` environment variable

```bash
export DEBUG_LOG_FILE="/tmp/my-custom-debug.log"
source .github/scripts/debug/debug-helpers.sh
log_info "This goes to /tmp/my-custom-debug.log"
```

## 🎯 Best Practices

1. **Always source debug-helpers.sh** before using logging functions
2. **Set WORKFLOW_CONTEXT** to identify which part of code is running
3. **Use appropriate log levels** - debug for details, info for important messages
4. **Collect artifacts** in CI/CD to preserve debug information
5. **Check diagnostics early** when troubleshooting issues
6. **Clean up logs** periodically (use artifact retention policies)

## 📚 Related Documentation

- [GitHub Actions Debugging](https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows)
- [Tailpaste Health Monitoring](../../health-check/)
- [Workflow Troubleshooting Guide](../../../docs/CI_CD.md)

