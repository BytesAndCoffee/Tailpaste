# CI/CD Workflows

Automated CI/CD pipeline for Tailpaste using GitHub Actions with self-hosted runners (GitHub ARC on Kubernetes).

## Architecture

**Runners**: GitHub Actions Runner Controller (ARC) running in Kubernetes on `plex` host
**Target**: Docker host running the tailpaste container
**Network**: Tailscale for secure connectivity

### Runner Requirements

The ARC runner pods must be configured with:
- `privileged: true` OR
- Capabilities: `NET_ADMIN`, `NET_RAW`, `SYS_MODULE`
- Access to `/dev/net/tun`

This is required for Tailscale kernel networking mode.

**Important:** ARC runners always include the `self-hosted` label. Workflows must explicitly request both `self-hosted` AND the custom label:

```yaml
runs-on:
  - self-hosted
  - tailpaste-runners
```

**Example ARC runner configuration:**
```yaml
spec:
  template:
    spec:
      containers:
      - name: runner
        securityContext:
          privileged: true
        # OR use specific capabilities:
        # securityContext:
        #   capabilities:
        #     add:
        #     - NET_ADMIN
        #     - NET_RAW
        #     - SYS_MODULE
```

## Workflow Dependencies & Execution Order

See [../../docs/CI_CD.md](../../docs/CI_CD.md) for complete CI/CD pipeline documentation including:
- Complete workflow dependency chain
- Task execution order and timing
- Monitoring and deployment procedures
- Best practices and troubleshooting

### Quick Overview

```
Push/PR → [CI: Lint & Test] → [CI: Docker Build] → [Integration Tests] → [Deploy]
                                                   ↗
                                    [Security Scans] (parallel)
```

**Release Flow:**
```
Tag → [Validate] → [Security + Build] → [Create Artifacts] → [Publish]
```

## Workflows

### 1. CI - Continuous Integration (`ci.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main`

**Jobs:**

#### `lint-and-test`
- Linting with flake8
- Code formatting check with black
- Type checking with mypy
- Security scanning with bandit
- Unit tests with pytest
- Code coverage reporting (70% threshold)
- Upload coverage to Codecov (optional)

#### `docker-build`
- Build Docker image with commit SHA tag
- Test image imports
- Report image size

**Duration:** ~3-5 minutes

### 2. Deploy - Continuous Deployment (`deploy.yml`)

**Triggers:**
- Push to `main` branch
- Manual workflow dispatch

**Process:**
1. Connect to Tailscale network
2. SSH to `docker` host
3. Pull latest code from GitHub
4. Rebuild Docker image
5. Restart container with docker-compose
6. Verify deployment
7. Test service health

**Duration:** ~2-3 minutes

**Requirements:**
- Tailscale OAuth credentials in secrets
- SSH access to `docker` host via Tailscale
- Git repository cloned at `~/tailpaste` on docker host

### 3. Integration Tests (`integration-test.yml`)

**Triggers:**
- Push to `main` branch
- Every 6 hours (scheduled)
- Manual workflow dispatch

**Tests:**
- Service availability check
- Basic paste creation and retrieval
- Large paste handling (500KB)
- Concurrent request handling
- Security: Proxy header rejection (403 responses)

**Duration:** ~1-2 minutes

## Setup

### Prerequisites

1. **GitHub ARC Runners**
   - Installed in Kubernetes on `plex` host
   - Label: `tailpaste-runners`
   - Has access to Docker daemon

2. **Tailscale Configuration**
   - OAuth client created with `devices:write` scope
   - Tagged with `tag:ci`
   - ACL allows `tag:ci` to access `docker` host

3. **Docker Host Setup**
   - Repository cloned at `~/tailpaste`
   - SSH access via Tailscale
   - Docker and docker-compose installed

### Required Secrets

Configure these in GitHub repository settings:

| Secret | Description | Required For |
|--------|-------------|--------------|
| `TS_OAUTH_CLIENT_ID` | Tailscale OAuth client ID | Deploy, Integration Tests |
| `TS_OAUTH_SECRET` | Tailscale OAuth secret | Deploy, Integration Tests |
| `CODECOV_TOKEN` | Codecov upload token | CI (optional) |

**To add secrets:**
1. Go to repository Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add each secret with its value

### Tailscale OAuth Setup

1. Go to [Tailscale Admin Console](https://login.tailscale.com/admin/settings/oauth)
2. Click "Generate OAuth client"
3. Configure:
   - **Scopes**: `devices:write`
   - **Tags**: `tag:ci`
4. Copy Client ID and Secret to GitHub secrets

### ACL Configuration

Ensure your Tailscale ACL includes:

```json
{
  "tagOwners": {
    "tag:ci": ["your-email@example.com"]
  },
  "ssh": [
    {
      "action": "accept",
      "src": ["tag:ci"],
      "dst": ["tag:vps"],
      "users": ["autogroup:nonroot"]
    }
  ]
}
```

## Workflow Status

View workflow runs:
- Repository → Actions tab
- See status badges in main README

## Manual Triggers

All workflows support manual triggering:

1. Go to Actions tab
2. Select workflow
3. Click "Run workflow"
4. Choose branch
5. Click "Run workflow"

### Troubleshooting

### Tailscale Connection Failures

**Error: "sudo failed with exit code 1" or "runner is not in the sudoers file"**

The runner pod needs elevated privileges to run Tailscale in kernel networking mode.

**Solution**: Update your ARC runner configuration to run as privileged:

```bash
# Edit your ARC runner scale set
kubectl edit runnerscaleset tailpaste-runners -n actions-runner-system

# Add under spec.template.spec.containers[0]:
securityContext:
  privileged: true
```

Or use specific capabilities if you don't want full privileged mode:
```yaml
securityContext:
  capabilities:
    add:
    - NET_ADMIN
    - NET_RAW
    - SYS_MODULE
```

### CI Failures

**Linting errors:**
```bash
# Run locally
flake8 src/ tests/ --max-line-length=120
black src/ tests/
```

**Test failures:**
```bash
# Run locally
pytest tests/ -v
```

**Coverage below threshold:**
```bash
# Check coverage
pytest --cov=src tests/ --cov-report=term-missing
```

### Deploy Failures

**SSH connection issues:**
- Verify Tailscale OAuth credentials are correct
- Check ACL allows `tag:ci` → `docker` host
- Verify runner has network connectivity

**Container won't start:**
```bash
# Check logs on docker host
ssh docker
cd ~/tailpaste
docker logs tailpaste --tail=100
```

**Git pull fails:**
```bash
# Ensure repo is clean on docker host
ssh docker
cd ~/tailpaste
git status
git reset --hard origin/main
```

### Integration Test Failures

**Service not reachable:**
- Verify tailpaste container is running
- Check Tailscale connection in runner
- Verify hostname `tailpaste` resolves correctly

**Paste creation fails:**
- Check container logs for errors
- Verify Tailscale authentication is working
- Test manually: `curl -X POST -d "test" http://tailpaste:8080/`

**Proxy header tests fail:**
- Verify security middleware is enabled
- Check app.py has proxy header detection

## Monitoring

### Workflow Notifications

GitHub automatically notifies on:
- Workflow failures
- First successful run after failures

Configure additional notifications:
- Repository Settings → Notifications
- Watch repository for Actions

### Logs

Access workflow logs:
1. Actions tab
2. Click workflow run
3. Click job name
4. Expand step to see logs

Logs are retained for 90 days.

## Best Practices

### Development Workflow

1. Create feature branch
2. Make changes
3. Push to GitHub
4. CI runs automatically
5. Review CI results
6. Merge to main
7. Deploy runs automatically

### Testing Before Merge

- CI runs on all PRs
- Ensure all checks pass before merging
- Review coverage reports

### Deployment Safety

- Deploy only runs on `main` branch
- Manual approval not required (auto-deploy)
- Rollback: revert commit and push

### Monitoring

- Check Actions tab regularly
- Review integration test results
- Monitor for recurring failures

## Performance

**Typical run times:**
- CI: 3-5 minutes
- Deploy: 2-3 minutes  
- Integration Tests: 1-2 minutes

**Optimization tips:**
- Use pip cache (already configured)
- Minimize Docker image layers
- Run tests in parallel where possible

## Security

**Secrets Management:**
- Never commit secrets to repository
- Use GitHub secrets for sensitive data
- Rotate Tailscale OAuth credentials periodically

**Network Security:**
- All communication via Tailscale (encrypted)
- No public endpoints exposed
- SSH via Tailscale only

**Container Security:**
- Regular security scans with bandit
- Keep dependencies updated
- Review Dependabot alerts

## Future Enhancements

Potential improvements:
- [ ] Add staging environment
- [ ] Implement blue-green deployments
- [ ] Add performance benchmarking
- [ ] Integrate with monitoring/alerting
- [ ] Add automatic rollback on failure
- [ ] Multi-architecture Docker builds
- [ ] Container image scanning (Trivy)
- [ ] Automated dependency updates

## Support

For issues with workflows:
1. Check workflow logs in Actions tab
2. Review this documentation
3. Test components manually
4. Check Tailscale connectivity
5. Verify secrets are configured correctly
