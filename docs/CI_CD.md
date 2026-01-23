# CI/CD Documentation

Complete documentation for the Tailpaste CI/CD pipeline, workflows, scripts, and best practices.

## Table of Contents

- [Overview](#overview)
- [Quick Reference](#quick-reference)
- [Workflow Architecture](#workflow-architecture)
- [GitHub Actions Workflows](#github-actions-workflows)
- [Monitoring Scripts](#monitoring-scripts)
- [Development Tools](#development-tools)
- [Best Practices](#best-practices)

## Overview

The Tailpaste CI/CD pipeline provides automated testing, security scanning, deployment, and monitoring with:

- **Multi-version testing** across Python 3.10, 3.11, and 3.12
- **Security scanning** for dependencies, code, and containers
- **Automated deployments** with rollback capability
- **Release management** with semantic versioning
- **Health monitoring** and alerting
- **Pre-commit hooks** for code quality

**Infrastructure**: Self-hosted GitHub Actions runners via ARC (Actions Runner Controller) on Kubernetes

## Quick Reference

### Common Commands

```bash
# Development
pytest tests/ -v                          # Run tests
black src/ tests/                         # Format code
flake8 src/ tests/                        # Lint code
mypy src/                                 # Type check

# Monitoring
python3 scripts/health_check.py           # Health check
python3 scripts/log_analyzer.py           # Analyze logs

# Git Workflow
git checkout -b feature/my-feature        # Create branch
git commit -m "feat: add feature"         # Commit (hooks run)
git push origin feature/my-feature        # Push (triggers CI)

# Releases
git tag v1.0.0                           # Create release tag
git push origin v1.0.0                   # Push tag (triggers release)

# Manual Workflows
# GitHub Actions → Workflow → Run workflow
```

### Workflow Triggers

| Workflow | Trigger | Duration | Purpose |
|----------|---------|----------|---------|
| **CI** | Push, PR | 5-8 min | Testing & build |
| **Integration Tests** | CI success | 2-3 min | End-to-end testing |
| **Security** | Push, PR, Daily | 3-5 min | Vulnerability scanning |
| **Deploy** | Integration success | 3-5 min | Production deployment |
| **Release** | Version tag | 10-15 min | Release & deployment |
| **Health Check** | Hourly | 1-2 min | Service monitoring & auto-recovery |

### Key Paths

- Workflows: `.github/workflows/`
- Scripts: `scripts/`
- Logs: `docker logs tailpaste`
- Storage: `./storage/`
- Backups: `~/.tailpaste-backups/`

## Workflow Architecture

### Dependency Chain

```
┌─────────────────────────────────────────────────────────────────┐
│                         CI PIPELINE                              │
│  ┌──────────────────┐                                            │
│  │ Lint & Test      │ → Matrix: Python 3.10, 3.11, 3.12         │
│  │ (All Versions)   │    - Code quality checks                  │
│  └────────┬─────────┘    - Type checking                        │
│           │              - Unit tests + coverage                 │
│           ↓                                                       │
│  ┌──────────────────┐                                            │
│  │ Docker Build     │ → Build & test image                      │
│  └──────────────────┘                                            │
└─────────────────────────────────────────────────────────────────┘
                    ↓
        ┌──────────────────────┐
        │ Integration Tests    │ (On CI success)
        │                      │  - Service availability
        │                      │  - Paste operations
        └──────────┬───────────┘  - End-to-end tests
                   ↓
        ┌──────────────────────┐
        │ Security Scanning    │ (Parallel)
        │                      │  - Dependencies
        │                      │  - Code analysis
        └──────────┬───────────┘  - Container scanning
                   ↓
        ┌──────────────────────┐
        │ Deploy               │ (On success)
        │                      │  - Backup
        │                      │  - Deploy
        └──────────────────────┘  - Health check

┌─────────────────────────────────────────────────────────────────┐
│                   CONTINUOUS MONITORING                          │
│  ┌──────────────────┐                                            │
│  │ Health Check     │ → Hourly automated checks                 │
│  │ (Hourly Cron)    │    - Service availability                 │
│  └────────┬─────────┘    - Database integrity                   │
│           │              - Tailscale connectivity                │
│           ↓                                                       │
│  ┌──────────────────┐                                            │
│  │ Auto-Recovery    │ → On failure: trigger deploy             │
│  └──────────────────┘                                            │
└─────────────────────────────────────────────────────────────────┘
```

### Release Pipeline

```
┌──────────────────┐
│ Tag Push         │ (v*.*.*)
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Validate Release │ → Version format check
└────────┬─────────┘
         ↓
    ┌────┴────┐
    ↓         ↓
┌─────────┐ ┌─────────┐
│Security │ │  Build  │ (Parallel)
│  Scans  │ │ & Test  │
└────┬────┘ └────┬────┘
     └─────┬─────┘
           ↓
┌──────────────────┐
│ Create Artifacts │ → Archive, checksums, installer
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Publish Release  │ → GitHub Release with notes
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Deploy Release   │ → Production deployment
└──────────────────┘
```

### Task Execution Matrix

| Task | Depends On | Duration | Parallel | Fail-Fast |
|------|-----------|----------|----------|-----------|
| **Lint & Test** | None | 3-5 min | ✅ (matrix) | No |
| **Docker Build** | Lint & Test | 2-3 min | ❌ | Yes |
| **Integration Tests** | CI Success | 2-3 min | ❌ | Yes |
| **Security Scans** | None | 3-5 min | ✅ | No |
| **Deploy** | Integration | 3-5 min | ❌ | Yes |
| **Release Build** | Validate | 5-8 min | ✅ | No |

## GitHub Actions Workflows

### CI Workflow

**File**: `.github/workflows/ci.yml`

**Triggers**:
- Push to `main`, `develop`
- Pull requests to `main`

**Features**:
- Matrix testing (Python 3.10, 3.11, 3.12)
- Parallel execution with caching
- Code quality (flake8, black, mypy, bandit)
- 70% minimum test coverage
- Docker build and vulnerability scanning
- Automated summaries

**Matrix Strategy**:
```yaml
strategy:
  fail-fast: false
  matrix:
    python-version: ['3.10', '3.11', '3.12']
```

**Artifacts**:
- Coverage reports (XML, HTML)
- Test results (JUnit XML)
- Security scans (flake8, mypy, bandit, trivy)

**Benefits**:
- Catches Python version incompatibilities
- 30-50% faster builds with caching
- Early vulnerability detection

### Integration Tests Workflow

**File**: `.github/workflows/integration-test.yml`

**Triggers**:
- After CI workflow completes successfully
- Scheduled daily at 1 AM UTC
- Manual dispatch

**Tests**:
- Service availability and health
- Paste creation and retrieval
- Large paste handling (up to 1MB)
- Public read access
- Error handling scenarios

**Conditions**:
- Only runs if CI succeeded
- Skipped if CI failed
- Can be run manually anytime

### Security Workflow

**File**: `.github/workflows/security.yml`

**Triggers**:
- Push and pull requests
- Daily at 2 AM UTC
- Manual dispatch

**Jobs** (all parallel):
1. **Dependency Scan**: Safety + pip-audit
2. **Code Security**: Bandit analysis
3. **Container Scan**: Trivy image scanning
4. **Dependency Updates**: Outdated packages (scheduled only)

**Artifacts**:
- Vulnerability reports
- Security analysis results
- Container scan results
- Outdated packages list

**Benefits**:
- Proactive security monitoring
- Automated vulnerability tracking
- Compliance with security best practices

#### Trivy Filesystem Scanning

The pipeline uses **filesystem scanning** instead of Docker image scanning to prevent disk exhaustion on remote Docker daemons while maintaining full security coverage.

**Why Filesystem Scanning?**
- Docker image scanning requires exporting layers, consuming significant disk space on remote daemons (via Tailscale)
- Filesystem scanning checks the source code directly without Docker layer exports
- Faster and more reliable on remote hosts
- Supports both vulnerability and secret detection

**Configuration**:
```yaml
scan-type: fs
scanners: vuln,secret
severity: HIGH,CRITICAL
skip-dirs: .git,htmlcov,__pycache__
```

**Excluded Directories** (`.trivyignore`):
- Version control: `.git`, `.github`
- Python cache: `__pycache__`, `*.pyc`
- Test artifacts: `htmlcov`, `.coverage`
- Virtual environments: `venv`, `env`
- Documentation and reports

**Cleanup Strategy**:
After Docker builds, the pipeline automatically cleans up testing resources:
```bash
# Remove only testing-labeled resources
docker ps -a --filter "label=environment=testing" --filter "label=managed-by=ci" -q | xargs -r docker rm -f
docker images --filter "label=environment=testing" -q | xargs -r docker rmi -f
docker volume ls --filter "label=environment=testing" -q | xargs -r docker volume rm
# Prune dangling resources (safe for production)
docker image prune -f
docker container prune -f
```

This cleanup runs even if previous steps fail (`if: always()`) and never fails the job (`|| true`).

### Deployment Workflow

**File**: `.github/workflows/deploy.yml`

**Triggers**:
- After integration tests succeed
- Manual dispatch (with rollback option)
- Can be called from release workflow

**Process**:
1. Create backup (database, image, git state)
2. Pull latest changes
3. Build new Docker image
4. Deploy container
5. Run health checks
6. Test service availability
7. Generate summary

**Rollback**:
- Actions → Deploy → Run workflow → Enable rollback
- Restores: database, git commit, Docker image

**Health Checks**:
- HTTP endpoint availability
- Response time validation
- Paste creation test
- Database integrity

### Health Check Workflow

**File**: `.github/workflows/health-check.yml`

**Triggers**:
- Scheduled hourly (at minute 0)
- Manual dispatch for testing

**Features**:
- Automated service availability checks
- Database integrity verification
- Tailscale connectivity validation
- Docker logs analysis
- Automatic recovery via deploy trigger

**Process**:
1. Connect to Tailscale network
2. Run comprehensive health checks using `scripts/health_check.py`
3. Export results as artifacts
4. If any check fails, automatically trigger deployment workflow
5. Generate detailed summary reports

**Auto-Recovery**:
When health checks fail, the workflow automatically:
- Triggers the deploy workflow to redeploy the service
- Generates notifications with failure details
- Provides actionable next steps for manual intervention if needed

**Manual Testing**:
```bash
# Test locally
python3 scripts/health_check.py

# Run workflow manually
# GitHub Actions → Health Check → Run workflow
```

**Health Check Results**:
- Stored as artifacts for 30 days
- JSON format for integration with monitoring tools
- Detailed logs in GitHub Actions summary

### Release Workflow

**File**: `.github/workflows/release.yml`

**Triggers**:
- Git tags matching `v*.*.*`
- Manual dispatch with version input

**Process**:
1. Validate version format (X.Y.Z)
2. Run security scans and tests
3. Build and tag Docker image
4. Generate changelog
5. Create distribution archive
6. Generate SHA256 checksums
7. Create installation script
8. Publish GitHub Release
9. Deploy to production

**Creating a Release**:
```bash
git tag v1.0.0
git push origin v1.0.0
```

**Release Artifacts**:
- `tailpaste-{version}.tar.gz` - Source distribution
- `tailpaste-{version}.tar.gz.sha256` - Checksum
- `install.sh` - Installation script
- `CHANGELOG.md` - Generated changelog

## Monitoring Scripts

### Health Check Script

**File**: `scripts/health_check.py`

**Usage**:
```bash
python3 scripts/health_check.py                  # Run check
python3 scripts/health_check.py --export report.json  # Export
python3 scripts/health_check.py --silent         # Summary only
```

**Configuration** (`health_check_config.json`):
```json
{
  "service_url": "http://localhost:8080",
  "storage_path": "./storage",
  "max_db_size_mb": 500,
  "response_timeout": 10,
  "critical_error_threshold": 10,
  "tailscale_check": true
}
```

**Checks**:
- ✅ HTTP availability
- ✅ Response time
- ✅ Database integrity
- ✅ Storage size
- ✅ Paste statistics
- ✅ Tailscale status
- ✅ Docker logs analysis

### Log Analyzer Script

**File**: `scripts/log_analyzer.py`

**Usage**:
```bash
python3 scripts/log_analyzer.py                       # Last 1000 lines
python3 scripts/log_analyzer.py --lines 5000          # Specific count
python3 scripts/log_analyzer.py --container prod      # Different container
python3 scripts/log_analyzer.py --export report.json  # Export report
python3 scripts/log_analyzer.py --errors-only         # Errors only
```

**Metrics**:
- Total requests and methods
- Status code distribution
- Top request paths
- Unique IP addresses
- Error categorization
- Warning count

**Error Categories**:
- Database errors
- Network issues
- Tailscale problems
- Authentication failures
- Python exceptions
- Disk errors

### Monitoring Script

**File**: `scripts/monitor.sh`

**Usage**:
```bash
./scripts/monitor.sh
```

**Configuration** (environment variables):
```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/..."
export EMAIL_ALERT="admin@example.com"
export ALERT_ON_WARNING="true"
export STORAGE_PATH="./storage"
```

**Features**:
- Automated health checks
- Log analysis
- Disk space monitoring
- Container status
- Alert notifications (Slack/Email)
- Automated log cleanup

**Cron Schedule**:
```bash
*/5 * * * * /path/to/Tailpaste/scripts/monitor.sh    # Every 5 minutes
0 * * * * /path/to/Tailpaste/scripts/monitor.sh      # Every hour
```

**Alerts For**:
- Service unavailability
- Health check failures
- High error counts (>10)
- Critical disk space (>90%)
- Container not running

## Development Tools

### Pre-commit Hooks

**Setup**:
```bash
./scripts/setup-hooks.sh
```

**Hooks Installed**:

1. **pre-commit** (`scripts/pre-commit-hook.py`)
   - Black formatting validation
   - Flake8 linting
   - Mypy type checking
   - Test file checks
   - Full test suite

2. **commit-msg**
   - Minimum 10 characters
   - Optional conventional commits

3. **pre-push**
   - Full test suite before push

**Bypassing**:
```bash
git commit --no-verify    # Skip pre-commit
git push --no-verify      # Skip pre-push
```

### Workflow Validation

**Script**: `scripts/validate-workflows.py`

Validates GitHub Actions workflow syntax and structure.

## Best Practices

### Docker Label Strategy

All Docker resources are explicitly labeled to prevent CI/CD workflows from accidentally affecting production containers, images, and volumes.

**Label Schema**:

Testing/CI Resources (`docker-compose.test.yml`):
```yaml
labels:
  - "environment=testing"
  - "managed-by=ci"
```

Production Resources (`docker-compose.yml`):
```yaml
labels:
  - "environment=production"
  - "managed-by=manual"
```

**Safety Mechanisms**:

1. **Targeted Cleanup**: All CI workflows use label filters
   ```bash
   # ✅ SAFE: Only removes testing resources
   docker ps -a --filter "label=environment=testing" --filter "label=managed-by=ci" -q | xargs -r docker rm -f
   
   # ❌ UNSAFE: Would remove ALL containers
   docker ps -a -q | xargs docker rm -f
   ```

2. **Production Protection**: Production resources have different labels (`environment=production`, `managed-by=manual`) so they're never matched by CI cleanup commands

3. **Image Tagging**:
   - Testing: `tailpaste-app:testing`
   - Production: `tailpaste-app:production`
   - Versioned: `tailpaste-app:v1.0.0`

**Verification**:
```bash
# View containers with labels
docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Labels}}"

# View only testing containers
docker ps -a --filter "label=environment=testing"

# View only production containers
docker ps -a --filter "label=environment=production"
```

**Benefits**:
- Zero risk of accidental production disruption
- Clear resource ownership
- Automated cleanup safety
- Built-in audit trail

### Development Workflow

1. **Create feature branch**:
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes**: Pre-commit hooks run automatically

3. **Push changes**: Triggers CI workflow

4. **Create PR**: Full test matrix and security scans

5. **Merge to main**: Auto-deployment after tests pass

### Release Process

1. **Prepare release**:
   - Update version numbers
   - Update changelog
   - Test thoroughly

2. **Create tag**:
   ```bash
   git tag v1.2.3
   git push origin v1.2.3
   ```

3. **Monitor release**: Check GitHub Actions for progress

4. **Verify deployment**: Test production service

### Monitoring

1. **Automated hourly checks**: GitHub Actions Health Check workflow runs automatically every hour

2. **Manual health checks**: Run health checks on-demand locally or via workflow dispatch

3. **Log analysis**: Daily review for errors and trends

4. **Disk management**: Monitor storage and archive logs

5. **Security**: Review daily scans and update dependencies

### Security

1. **Dependencies**: Review scans, update regularly, test updates

2. **Secrets**: Use GitHub Secrets, rotate keys, never commit

3. **Access**: Limit permissions, least privilege principle

4. **Containers**: Scan images, use official bases, keep updated

### Rollback Procedures

**When to Rollback**:
- Critical bugs in production
- Service unavailability
- Failed health checks
- Data corruption

**How to Rollback**:
1. GitHub Actions → Deploy workflow
2. Run workflow → Enable "Rollback to previous version"
3. Monitor logs
4. Verify health

**What's Restored**:
- Database state
- Git commit
- Docker image
- Configuration

## Troubleshooting

### CI Failures

**Tests failing**:
```bash
pytest tests/ -v              # Run locally
pytest --cov=src tests/       # Check coverage
```

**Linting issues**:
```bash
black src/ tests/             # Fix formatting
flake8 src/ tests/            # Check linting
mypy src/                     # Type checking
```

**Docker build fails**:
```bash
docker compose -f docker-compose.test.yml build
docker compose -f docker-compose.test.yml logs
```

### Deployment Issues

**Rollback fails**:
- Check `~/.tailpaste-backups` exists
- Verify backup integrity
- Manual: `git reset --hard <commit>`

**Health checks fail**:
- Check container: `docker ps`
- View logs: `docker logs tailpaste`
- Test: `curl http://tailpaste:8080/`

**Service unavailable**:
- Check Tailscale: `tailscale status`
- Test network: `ping tailpaste`
- Check firewall rules

### Monitoring Issues

**Scripts not executable**:
```bash
chmod +x scripts/*.sh scripts/*.py
```

**Dependencies missing**:
```bash
pip install -r requirements.txt
```

**Docker permission denied**:
```bash
sudo usermod -aG docker $USER
```

## Configuration

### GitHub Secrets

```yaml
TS_OAUTH_CLIENT_ID: OAuth client ID for Tailscale
TS_OAUTH_SECRET: OAuth secret for Tailscale
TAILSCALE_AUTHKEY: Ephemeral auth key
SLACK_WEBHOOK_URL: Optional Slack webhook for alerts
```

### Environment Variables

```bash
# Service
STORAGE_PATH=./storage
LISTEN_PORT=8080
CUSTOM_DOMAIN=paste.example.com

# Monitoring
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
EMAIL_ALERT=admin@example.com
ALERT_ON_WARNING=true
TAILPASTE_URL=http://tailpaste:8080
```

### Runner Requirements

Self-hosted runners need:
- Docker and Docker Compose
- Python 3.10+ with pip
- Tailscale client
- Git
- Standard Unix tools

**Labels**: `self-hosted`, `tailpaste-runners`

## Continuous Improvement

### Metrics to Track

- Test coverage percentage
- Build/deployment success rate
- Time to deploy
- Rollback frequency
- Security vulnerabilities
- Mean time to recovery (MTTR)

### Future Enhancements

- [ ] External monitoring integration (Datadog, New Relic)
- [ ] Automated performance testing
- [ ] Blue-green deployments
- [ ] Canary deployments
- [ ] Multi-region support
- [ ] Automated database migrations
- [ ] Load testing in CI

---

**Last Updated**: January 20, 2026 | **Version**: 1.0.0
