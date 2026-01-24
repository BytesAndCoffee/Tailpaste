# Tailpaste Scripts

Organized collection of automation and management scripts for Tailpaste CI/CD, development, and operations.

## Directory Structure

```
scripts/
├── ci/              # CI/CD pipeline scripts
├── dev/             # Development tools
├── health/          # Health monitoring & diagnostics
├── workflows/       # GitHub Actions workflow helpers
└── README.md        # This file
```

## Quick Start

### Development Setup

```bash
# Install Git hooks for code quality
./scripts/dev/setup-hooks.sh

# Run cleanup
./scripts/dev/cleanup.sh
```

### Health Monitoring

```bash
# Run health check
python3 scripts/health/health_check.py

# Analyze logs
python3 scripts/health/log_analyzer.py

# Start monitoring
./scripts/health/monitor.sh
```

### CI/CD Operations

```bash
# Check artifact status
python3 scripts/ci/artifact_manager.py get-status --digest <digest>

# Check circuit breaker
python3 scripts/ci/circuit_breaker.py status

# Generate rollback plan
python3 scripts/ci/rollback_manager.py plan
```

## Scripts by Category

### 📁 ci/ - CI/CD Pipeline

| Script | Description |
|--------|-------------|
| `artifact_manager.py` | Artifact lifecycle management |
| `circuit_breaker.py` | Circuit breaker management |
| `rollback_manager.py` | Rollback planning and execution |
| `manual_action_manager.py` | Manual action logging and auditing |
| `test_workflow_failure_handling.py` | Test failure simulation |
| `ci` | Local CI runner script |
| `fix-ci` | Auto-fix CI issues |

**Usage Examples:**

```bash
# Artifact management
python3 scripts/ci/artifact_manager.py check-existing --commit abc123
python3 scripts/ci/artifact_manager.py record-artifact --commit abc123 --digest sha256:...

# Circuit breaker
python3 scripts/ci/circuit_breaker.py status
python3 scripts/ci/circuit_breaker.py reset --type recovery

# Rollback
python3 scripts/ci/rollback_manager.py plan --target-version v1.2.3
python3 scripts/ci/rollback_manager.py validate
```

### 🔧 dev/ - Development Tools

| Script | Description |
|--------|-------------|
| `pre-commit-hook.py` | Code quality checks before commits |
| `setup-hooks.sh` | Install Git hooks |
| `cleanup.sh` | Clean cache and temporary files |
| `validate-workflows.py` | Validate GitHub Actions YAML |
| `validate_artifact_workflow.py` | Validate artifact workflow |
| `validate_ci_gating.py` | Validate CI quality gates |

**Usage Examples:**

```bash
# Setup development environment
./scripts/dev/setup-hooks.sh

# Validate workflows
python3 scripts/dev/validate-workflows.py

# Clean up project
./scripts/dev/cleanup.sh
```

### 🏥 health/ - Health Monitoring

| Script | Description |
|--------|-------------|
| `health_check.py` | Comprehensive health monitoring |
| `health_monitor.py` | Health monitoring utility for CI/CD |
| `log_analyzer.py` | Docker log analysis |
| `monitor.sh` | Unified monitoring script |
| `parse_health_results.py` | Parse health check JSON |
| `update_health_history.py` | Update health check history |
| `count_consecutive_degraded.py` | Count degraded checks |

**Usage Examples:**

```bash
# Basic health check
python3 scripts/health/health_check.py

# Export results
python3 scripts/health/health_check.py --export /tmp/health.json

# Parse results
python3 scripts/health/parse_health_results.py /tmp/health.json overall_status

# Monitor service
./scripts/health/monitor.sh
```

### 🔄 workflows/ - Workflow Helpers

| Script | Description |
|--------|-------------|
| `workflow_status_monitor.py` | Workflow status monitoring and reporting |
| `workflow_error_handler.py` | Workflow error handling |
| `orchestration_helper.py` | Workflow orchestration utilities |

**Usage Examples:**

```bash
# Monitor workflow status
python3 scripts/workflows/workflow_status_monitor.py --repository owner/repo

# Get workflow health
python3 scripts/workflows/workflow_status_monitor.py status ci

# Handle workflow errors
python3 scripts/workflows/workflow_error_handler.py analyze
```

## Common Operations

### Running Health Checks

```bash
# Quick health check
python3 scripts/health/health_check.py

# JSON output for automation
python3 scripts/health/health_check.py --json

# Silent mode (only summary)
python3 scripts/health/health_check.py --silent
```

### Managing Artifacts

```bash
# Check if artifact exists
python3 scripts/ci/artifact_manager.py check-existing \
  --commit $(git rev-parse HEAD)

# Record new artifact
python3 scripts/ci/artifact_manager.py record-artifact \
  --commit $(git rev-parse HEAD) \
  --digest sha256:abc123...

# Validate artifact in registry
python3 scripts/ci/artifact_manager.py validate-digest \
  --digest sha256:abc123...
```

### Circuit Breaker Operations

```bash
# Check status
python3 scripts/ci/circuit_breaker.py status

# Reset specific breaker
python3 scripts/ci/circuit_breaker.py reset --type deployment

# Increment failure count
python3 scripts/ci/circuit_breaker.py increment --type recovery
```

## Integration with GitHub Actions

These scripts integrate with GitHub Actions workflows:

- **CI**: [.github/workflows/ci.yml](../.github/workflows/ci.yml)
- **Integration Tests**: [.github/workflows/integration-test.yml](../.github/workflows/integration-test.yml)
- **Deploy**: [.github/workflows/deploy.yml](../.github/workflows/deploy.yml)
- **Health Monitoring**: [.github/workflows/health-monitor.yml](../.github/workflows/health-monitor.yml)
- **Recovery**: [.github/workflows/recovery.yml](../.github/workflows/recovery.yml)

## Environment Variables

Common environment variables used across scripts:

| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | GitHub API authentication |
| `GH_TOKEN` | Alternative GitHub token |
| `TAILPASTE_URL` | Tailpaste service URL |
| `STORAGE_PATH` | Storage directory path |
| `REGISTRY` | Container registry (ghcr.io) |
| `IMAGE_NAME` | Container image name |

## Development Guidelines

### Adding New Scripts

1. Place in appropriate subdirectory (`ci/`, `dev/`, `health/`, `workflows/`)
2. Add shebang line: `#!/usr/bin/env python3` or `#!/usr/bin/env bash`
3. Make executable: `chmod +x scripts/category/script.py`
4. Include docstring with description
5. Add `--help` argument support
6. Update this README with script description
7. Add tests if applicable

### Script Standards

- **Error Handling**: Use `set -euo pipefail` for bash scripts
- **Documentation**: Include header comments
- **Exit Codes**: 0 for success, non-zero for errors
- **Output**: Use emoji prefixes for visibility
- **JSON**: Export results to JSON when possible
- **Testing**: Add unit tests for Python scripts

## Testing

```bash
# Run script tests
pytest tests/test_health_check.py -v
pytest tests/test_artifact_manager.py -v

# Validate workflows
python3 scripts/dev/validate-workflows.py

# Test health checks
python3 scripts/health/health_check.py --silent
```

## Troubleshooting

### Permission Denied

```bash
chmod +x scripts/category/script.sh
```

### Python Module Not Found

```bash
pip install -r requirements.txt
```

### Script Not Working

1. Check script is executable
2. Verify dependencies installed
3. Review error messages
4. Check environment variables
5. Consult [docs/CI_CD.md](../docs/CI_CD.md)

## Related Documentation

- [CI/CD Documentation](../docs/CI_CD.md) - Complete CI/CD pipeline docs
- [Recovery System](../docs/RECOVERY_SYSTEM.md) - Recovery and redeployment
- [Inspector Guide](../docs/INSPECTOR_GUIDE.md) - Monitoring and debugging
- [GitHub Scripts README](../.github/scripts/README.md) - GitHub Actions scripts

## Support

For issues:
1. Check script help: `script.py --help`
2. Review error messages
3. Check logs directory
4. Consult documentation
5. Open GitHub issue

---

**Directory**: `/scripts`  
**Last Updated**: January 23, 2026  
**Maintainer**: Tailpaste Team
