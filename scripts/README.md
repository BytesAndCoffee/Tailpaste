# Tailpaste Scripts

This directory contains automation scripts for development, monitoring, and maintenance of the Tailpaste service.

## Scripts Overview

### Monitoring & Health

- **`health_check.py`** - Comprehensive health monitoring
- **`log_analyzer.py`** - Docker log analysis and metrics
- **`monitor.sh`** - Unified monitoring with alerting

### Development Tools

- **`pre-commit-hook.py`** - Code quality checks before commits
- **`setup-hooks.sh`** - Install Git hooks

## Quick Start

### Setup Git Hooks

```bash
./scripts/setup-hooks.sh
```

This installs pre-commit, commit-msg, and pre-push hooks for code quality.

### Run Health Check

```bash
# Basic health check
python3 scripts/health_check.py

# Export results
python3 scripts/health_check.py --export logs/health.json
```

### Analyze Logs

```bash
# Analyze recent logs
python3 scripts/log_analyzer.py

# Detailed analysis
python3 scripts/log_analyzer.py --lines 5000 --export logs/analysis.json
```

### Start Monitoring

```bash
# One-time monitoring cycle
./scripts/monitor.sh

# Schedule with cron (every 5 minutes)
*/5 * * * * /path/to/Tailpaste/scripts/monitor.sh
```

## Script Details

### health_check.py

**Purpose:** Monitor service health and database integrity

**Checks:**
- HTTP service availability
- Response time
- Database integrity
- Database size
- Tailscale connectivity
- Docker log errors

**Usage:**
```bash
python3 scripts/health_check.py [OPTIONS]

Options:
  --config PATH    Path to config file
  --export PATH    Export results to JSON
  --silent         Only output summary
```

**Exit codes:**
- `0` - All checks passed
- `1` - One or more checks failed

### log_analyzer.py

**Purpose:** Analyze Docker logs for errors and patterns

**Features:**
- Error categorization (database, network, auth, etc.)
- Request pattern analysis
- Status code distribution
- IP address tracking
- Performance metrics

**Usage:**
```bash
python3 scripts/log_analyzer.py [OPTIONS]

Options:
  --container NAME    Container name (default: tailpaste)
  --lines N          Number of lines (default: 1000)
  --export PATH      Export to JSON
  --errors-only      Show only errors
```

### monitor.sh

**Purpose:** Unified monitoring with alerting

**Features:**
- Runs health checks
- Analyzes logs
- Checks disk space
- Verifies container status
- Sends alerts (Slack/Email)
- Cleans up old logs

**Configuration:**
```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/..."
export EMAIL_ALERT="admin@example.com"
export ALERT_ON_WARNING="true"
export STORAGE_PATH="./storage"
```

### pre-commit-hook.py

**Purpose:** Enforce code quality before commits

**Checks:**
- Black code formatting
- Flake8 linting
- Mypy type checking
- Test file existence
- Test suite execution

**Automatic installation:** Run `./scripts/setup-hooks.sh`

### setup-hooks.sh

**Purpose:** Install Git hooks for development

**Installs:**
- `pre-commit` - Code quality checks
- `commit-msg` - Message validation
- `pre-push` - Test validation

**Usage:**
```bash
./scripts/setup-hooks.sh
```

## Configuration

### Health Check Config

Create `health_check_config.json`:
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

### Monitoring Alerts

Set environment variables:
```bash
# Slack webhook
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

# Email alerts
export EMAIL_ALERT="admin@example.com"

# Alert on warnings (not just errors)
export ALERT_ON_WARNING="true"
```

## Cron Examples

### Monitoring Schedule

```bash
# Every 5 minutes
*/5 * * * * /path/to/Tailpaste/scripts/monitor.sh

# Hourly
0 * * * * /path/to/Tailpaste/scripts/monitor.sh

# Daily at 2 AM
0 2 * * * /path/to/Tailpaste/scripts/monitor.sh
```

### Health Checks

```bash
# Every 15 minutes, export to JSON
*/15 * * * * python3 /path/to/Tailpaste/scripts/health_check.py --export /path/to/logs/health-$(date +\%Y\%m\%d-\%H\%M).json
```

### Log Analysis

```bash
# Daily log analysis at 1 AM
0 1 * * * python3 /path/to/Tailpaste/scripts/log_analyzer.py --export /path/to/logs/daily-$(date +\%Y\%m\%d).json
```

## Dependencies

All scripts require Python 3.8+ and standard system tools:

```bash
# Python packages (already in requirements.txt)
pip install pytest flake8 black mypy

# System tools
- docker
- curl
- jq (optional, for JSON parsing in bash)
- mail (optional, for email alerts)
```

## Log Files

Scripts create logs in `logs/` directory:

- `logs/monitor-YYYYMMDD.log` - Monitoring logs
- `logs/health-*.json` - Health check reports
- `logs/log-analysis-*.json` - Log analysis reports

**Log rotation:** Monitor script automatically cleans logs older than 30 days.

## Troubleshooting

### Scripts not executable

```bash
chmod +x scripts/*.sh scripts/*.py
```

### Python module not found

```bash
pip install -r requirements.txt
```

### Docker permission denied

```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Then logout and login
```

### Tailscale command not found

Health check will skip Tailscale check if CLI is not available. This is expected when running outside the container.

### No logs directory

Scripts automatically create the `logs/` directory when needed.

## Integration with CI/CD

These scripts are integrated into GitHub Actions workflows:

- **CI workflow** - Uses pre-commit checks
- **Security workflow** - Similar scanning logic
- **Deploy workflow** - Uses health checks for verification
- **Monitoring workflow** - Could trigger these scripts on schedule

See [docs/CI_CD.md](../docs/CI_CD.md) for details.

## Best Practices

1. **Run health checks regularly** - Set up cron jobs
2. **Monitor alerts** - Configure Slack/Email notifications
3. **Review logs weekly** - Check for patterns and trends
4. **Use pre-commit hooks** - Catch issues before committing
5. **Export reports** - Keep historical data for analysis
6. **Clean up old logs** - Let monitor script handle rotation

## Contributing

When adding new scripts:

1. Make executable: `chmod +x scripts/new_script.sh`
2. Add documentation to this README
3. Add to CI/CD documentation if relevant
4. Include error handling
5. Support `--help` option
6. Export results to JSON when possible

## Support

For issues with scripts:
1. Check script is executable
2. Verify dependencies installed
3. Review error messages
4. Check logs directory
5. Open a GitHub issue if needed

---

**Directory:** `/scripts`  
**Last Updated:** January 2026
