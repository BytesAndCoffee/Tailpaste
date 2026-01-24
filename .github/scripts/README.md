# GitHub Actions Workflow Scripts

This directory contains shell scripts extracted from GitHub Actions workflow files to improve maintainability, testability, and reduce inline code complexity.

## Directory Structure

```
.github/scripts/
├── README.md                           # This file
├── circuit-breaker/                    # Circuit breaker monitoring scripts
│   ├── cb-init-monitoring.sh           # Monitoring initialization
│   ├── cb-check-status.sh              # Status check
│   ├── cb-check-thresholds.sh          # Threshold monitoring
│   ├── cb-reset.sh                     # Circuit breaker reset
│   ├── cb-export-logs.sh               # Log export
│   ├── cb-generate-summary.sh          # Summary generation
│   └── cb-cleanup.sh                   # Cleanup
├── ci/                                 # CI/CD automation scripts
│   ├── ci-gating-validation.sh         # CI gating checks
│   ├── run-code-quality-checks.sh      # Code quality validation
│   └── run-tests-with-coverage.sh      # Test execution with coverage
├── deployment/                         # Deployment automation scripts
│   ├── deploy-enhanced-verification.sh # Enhanced deployment verification
│   ├── deploy-generate-health-report.sh # Health report generation
│   └── log-manual-action.sh            # Manual deployment/rollback logging
├── health-check/                       # Service health monitoring scripts
│   ├── run-health-check.sh             # Health check execution
│   ├── generate-health-summary.sh      # Summary generation
│   ├── notify-health-failure.sh        # Failure notification
│   ├── init-monitoring-session.sh      # Monitoring session initialization
│   ├── execute-health-checks.sh        # Comprehensive health check execution
│   └── record-health-results.sh        # Health check result recording
├── integration-test/                   # Integration testing scripts
│   ├── it-get-artifact.sh              # Artifact retrieval
│   ├── it-update-status.sh             # Status update
│   ├── it-install-tools.sh             # Tool installation
│   ├── it-check-elevation.sh           # Privilege check
│   ├── it-pull-artifact.sh             # Artifact pull
│   ├── it-wait-service.sh              # Service wait
│   ├── it-run-tests.sh                 # Test execution
│   ├── it-test-large-paste.sh          # Large paste testing
│   ├── it-test-security.sh             # Security checks
│   ├── it-record-results.sh            # Result recording
│   ├── it-mark-deployable.sh           # Deployability marking
│   └── it-generate-summary.sh          # Summary generation
└── parsers/                            # JSON/data parsing scripts
    ├── parse-deployment-verification.py # Deployment verification parser
    ├── parse-functionality-test.py     # Functionality test parser
    ├── parse-health-check.py           # Health check parser
    ├── parse-integration-status.py     # Integration status parser
    ├── parse-rollback-functionality.py # Rollback functionality parser
    ├── parse-rollback-health.py        # Rollback health parser
    └── parse-rollback-verification.py  # Rollback verification parser
```

## Script Categories

### CI Scripts (ci/)

Scripts for continuous integration, including code quality checks, testing, and gating validation.

**Usage in workflow:**
```yaml
- name: Run code quality checks
  run: |
    .github/scripts/ci/run-code-quality-checks.sh
```

**Key scripts:**
- `run-code-quality-checks.sh` - Executes linting and code quality validation
- `run-tests-with-coverage.sh` - Runs test suite with coverage reporting
- `ci-gating-validation.sh` - Validates CI gating requirements

### Health Check Scripts (health-check/)

Scripts for monitoring service health and triggering recovery workflows.

**Usage in workflow:**
```yaml
- name: Run health check
  run: |
    .github/scripts/health-check/run-health-check.sh
```

**Key scripts:**
- `run-health-check.sh` - Executes health check and exports results
- `generate-health-summary.sh` - Generates GitHub Actions summary
- `notify-health-failure.sh` - Creates failure notifications
- `init-monitoring-session.sh` - Initializes monitoring session
- `execute-health-checks.sh` - Executes comprehensive health checks
- `record-health-results.sh` - Records health check results

### Circuit Breaker Scripts (circuit-breaker/)

Scripts for managing circuit breaker state, monitoring thresholds, and preventing cascading failures.

**Usage in workflow:**
```yaml
- name: Check circuit breaker status
  run: |
    source .github/scripts/circuit-breaker/cb-check-status.sh "${{ github.repository }}" >> $GITHUB_OUTPUT
```

**Key scripts:**
- `cb-init-monitoring.sh` - Initializes monitoring session
- `cb-check-status.sh` - Checks comprehensive circuit breaker status
- `cb-check-thresholds.sh` - Monitors and auto-opens on threshold violations
- `cb-reset.sh` - Resets circuit breaker state
- `cb-export-logs.sh` - Exports logs and history
- `cb-generate-summary.sh` - Generates monitoring reports
- `cb-cleanup.sh` - Cleans up monitoring session

### Integration Test Scripts (integration-test/)

Scripts for running integration tests, verifying artifacts, and marking deployability.

**Usage in workflow:**
```yaml
- name: Run integration tests
  run: |
    .github/scripts/integration-test/it-run-tests.sh
```

**Key scripts:**
- `it-get-artifact.sh` - Retrieves artifact from CI workflow
- `it-update-status.sh` - Updates artifact status
- `it-pull-artifact.sh` - Pulls exact artifact for testing
- `it-run-tests.sh` - Runs basic integration tests
- `it-test-large-paste.sh` - Tests large paste handling
- `it-test-security.sh` - Tests security features
- `it-record-results.sh` - Records test results
- `it-mark-deployable.sh` - Marks artifacts as deployable/failed
- `it-generate-summary.sh` - Generates test summary

### Deployment Scripts (deployment/)

Scripts for production deployment verification, health reporting, and manual action logging.

**Usage in workflow:**
```yaml
- name: Generate deployment health report
  run: |
    .github/scripts/deployment/deploy-generate-health-report.sh
```

**Key scripts:**
- `deploy-enhanced-verification.sh` - Enhanced deployment verification
- `deploy-generate-health-report.sh` - Health report generation
- `log-manual-action.sh` - Manual deployment/rollback action logging

### Rollback Scripts (rollback/)

Scripts for managing manual rollback operations with lock management and validation.

**Usage in workflow:**
```yaml
- name: Acquire rollback lock
  run: |
    .github/scripts/rollback/mr-acquire-lock.sh
```

**Key scripts:**
- `mr-log-and-validate.sh` - Validates rollback request and logs initial state
- `mr-acquire-lock.sh` - Acquires deployment lock for rollback
- `mr-determine-target.sh` - Determines rollback target artifact
- `mr-release-lock.sh` - Releases deployment lock
- `mr-generate-summary.sh` - Generates rollback summary report

### Workflow Orchestration Scripts (workflows/)

Scripts for managing workflow dependencies and orchestration state.

**Usage in workflow:**
```yaml
- name: Initialize orchestration
  run: |
    .github/scripts/workflows/init-orchestration-session.sh
```

**Key scripts:**
- `init-orchestration-session.sh` - Initializes orchestration session
- `workflow_orchestrator.py` - Python class for workflow dependency validation
```yaml
- name: Run enhanced verification
  run: |
    scp .github/scripts/deployment/deploy-enhanced-verification.sh user@host:/tmp/
    ssh user@host "bash /tmp/deploy-enhanced-verification.sh"
```

**Key scripts:**
- `deploy-enhanced-verification.sh` - Comprehensive deployment verification
- `deploy-generate-health-report.sh` - Generates post-deployment health reports

### Parser Scripts (parsers/)

Python scripts for parsing JSON data and test results from workflows.

**Usage in workflow:**
```yaml
- name: Parse test results
  run: |
    RESULT=$(echo "$DATA" | python3 .github/scripts/parsers/parse-health-check.py)
```

**Key scripts:**
- `parse-deployment-verification.py` - Parses deployment verification results
- `parse-functionality-test.py` - Parses functionality test outputs
- `parse-health-check.py` - Parses health check status
- `parse-integration-status.py` - Parses integration test status
- `parse-rollback-*.py` - Parses rollback test results

## Benefits of Extraction

1. **Maintainability** - Scripts can be edited and versioned independently
2. **Testability** - Scripts can be tested locally before committing
3. **Reusability** - Common logic can be shared across workflows
4. **Readability** - Workflow files are cleaner and easier to understand
5. **Debugging** - Easier to debug script issues in isolation

## Development Guidelines

### Script Standards

1. **Error Handling** - All scripts should use `set -euo pipefail`
2. **Documentation** - Include header comments describing purpose and arguments
3. **Naming** - Use descriptive names with category prefix (e.g., `cb-`, `it-`)
4. **Permissions** - All scripts must be executable (`chmod +x`)
5. **Output** - Use consistent emoji prefixes for log messages

### Testing Locally

Scripts can be tested locally by setting required environment variables:

```bash
# Example: Testing health check script
export TAILPASTE_URL="http://localhost:8080"
export GITHUB_STEP_SUMMARY="/tmp/summary.md"
.github/scripts/run-health-check.sh
```

### Adding New Scripts

1. Create script in `.github/scripts/`
2. Add header comment with description and arguments
3. Make executable: `chmod +x .github/scripts/new-script.sh`
4. Update workflow to call script
5. Update this README with script documentation

## Environment Variables

Common environment variables used across scripts:

- `GITHUB_STEP_SUMMARY` - Path to GitHub Actions step summary
- `GITHUB_OUTPUT` - Path to GitHub Actions output file
- `GH_TOKEN` - GitHub token for API access
- `TAILPASTE_URL` - URL of Tailpaste service

## Related Files

- [health-check.yml](../workflows/health-check.yml) - Health monitoring workflow
- [circuit-breaker-monitor.yml](../workflows/circuit-breaker-monitor.yml) - Circuit breaker workflow
- [integration-test.yml](../workflows/integration-test.yml) - Integration testing workflow

## Troubleshooting

### Script Not Found

Ensure the script path is correct and starts with `.github/scripts/`

### Permission Denied

Make script executable:
```bash
chmod +x .github/scripts/script-name.sh
```

### Output Variables Not Set

When using `source` or expecting output variables, ensure you're redirecting to `$GITHUB_OUTPUT`:
```bash
source .github/scripts/script.sh >> $GITHUB_OUTPUT
```
