# Containerized CI/CD Orchestration - Quick Reference

**Location**: plex Tailscale host  
**API URL**: `http://plex.tailnet:5000`  
**Database**: SQLite at `/data/state/orchestration.db`  
**Documentation**: See `/docs/CONTAINERIZED_CICD*.md`

## One-Liner Setup

```bash
cd /opt/tailpaste && git checkout develop && \
mkdir -p /data/{state,logs,artifacts} && \
docker-compose -f docker-compose.orchestration.yml build && \
docker-compose -f docker-compose.orchestration.yml run --rm database-init && \
docker-compose -f docker-compose.orchestration.yml up -d && \
curl http://localhost:5000/api/health/status
```

## Core Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/trigger/ci` | Queue CI workflow |
| POST | `/api/trigger/integration-tests` | Queue integration tests |
| POST | `/api/trigger/deploy` | Queue deployment |
| GET | `/api/job/{id}` | Get job status |
| PATCH | `/api/job/{id}/status` | Update job status (internal) |
| POST | `/api/recovery/execute` | Execute recovery |
| POST | `/api/rollback/execute` | Execute rollback |
| GET | `/api/health/status` | System health |
| GET | `/api/state` | All state variables |
| POST | `/api/sync-variables` | Sync to GitHub |
| GET | `/api/admin/jobs` | List jobs |
| GET | `/api/admin/audit-log` | View audit trail |

## Trigger CI Job

```bash
curl -X POST http://plex.tailnet:5000/api/trigger/ci \
  -H "Content-Type: application/json" \
  -d '{
    "commit": "abc123",
    "branch": "main",
    "python_versions": ["3.10", "3.11", "3.12"],
    "github_run_id": "123456"
  }'

# Returns:
# {
#   "job_id": "ci-a1b2c3d4",
#   "status": "queued"
# }
```

## Check Job Status

```bash
curl http://plex.tailnet:5000/api/job/ci-a1b2c3d4 | jq '.'
```

## Common Operations

### View Logs
```bash
docker-compose -f docker-compose.orchestration.yml logs -f
docker-compose -f docker-compose.orchestration.yml logs -f api
```

### Database Query
```bash
docker-compose -f docker-compose.orchestration.yml exec api sqlite3 \
  /data/state/orchestration.db \
  "SELECT id, type, status, created_at FROM jobs ORDER BY created_at DESC LIMIT 10;"
```

### Restart Container
```bash
docker-compose -f docker-compose.orchestration.yml restart api
```

### Health Check
```bash
curl http://plex.tailnet:5000/api/health/status | jq '.'
```

### List Recent Jobs
```bash
curl http://plex.tailnet:5000/api/admin/jobs?limit=20 | jq '.jobs[] | {id, type, status}'
```

### View Audit Log
```bash
curl http://plex.tailnet:5000/api/admin/audit-log | jq '.entries[] | {timestamp, action, result}'
```

## Container Management

```bash
# Start all
docker-compose -f docker-compose.orchestration.yml up -d

# Stop all
docker-compose -f docker-compose.orchestration.yml down

# Status
docker-compose -f docker-compose.orchestration.yml ps

# Logs
docker-compose -f docker-compose.orchestration.yml logs -f

# Restart one
docker-compose -f docker-compose.orchestration.yml restart orchestrator

# Rebuild
docker-compose -f docker-compose.orchestration.yml build --no-cache
```

## Troubleshooting

### API Not Responding
```bash
# Check if running
docker-compose -f docker-compose.orchestration.yml ps

# Check logs
docker-compose -f docker-compose.orchestration.yml logs api

# Check port
lsof -i :5000

# Restart
docker-compose -f docker-compose.orchestration.yml restart api
```

### Database Issues
```bash
# Check integrity
docker-compose -f docker-compose.orchestration.yml exec api sqlite3 \
  /data/state/orchestration.db ".schema"

# Vacuum (optimize)
docker-compose -f docker-compose.orchestration.yml exec api sqlite3 \
  /data/state/orchestration.db "VACUUM;"

# Reinitialize if corrupted
docker-compose -f docker-compose.orchestration.yml down
docker volume rm cicd-state
docker-compose -f docker-compose.orchestration.yml run --rm database-init
docker-compose -f docker-compose.orchestration.yml up -d
```

### Stuck Job
```bash
# Manually update status
curl -X PATCH http://plex.tailnet:5000/api/job/ci-abc123/status \
  -H "Content-Type: application/json" \
  -d '{"status": "failure", "completed_at": "2026-01-27T15:30:00"}'
```

## Backup & Restore

### Backup
```bash
docker run --rm -v cicd-state:/data/state -v $(pwd):/backup \
  busybox cp /data/state/orchestration.db /backup/orchestration.backup.db
```

### Restore
```bash
docker-compose -f docker-compose.orchestration.yml down
docker volume rm cicd-state
docker volume create cicd-state
docker run --rm -v cicd-state:/data/state -v $(pwd):/backup \
  busybox cp /backup/orchestration.backup.db /data/state/orchestration.db
docker-compose -f docker-compose.orchestration.yml up -d
```

## Architecture at a Glance

```
GitHub Actions (Workflow Triggers)
    ↓ HTTP
plex:5000 (API Server)
    ↓ Reads/Writes
/data/state/orchestration.db (SQLite)
    ↑ Reads
Orchestrator (Health Check/Recovery)
Health Monitor (Metrics)
```

## Database Schema

```sql
-- Jobs: CI/test/deploy/recovery/rollback executions
CREATE TABLE jobs (
  id TEXT PRIMARY KEY,
  type TEXT,              -- 'ci', 'integration-tests', 'deploy', etc.
  status TEXT,            -- 'queued', 'running', 'success', 'failure'
  commit TEXT,
  version TEXT,
  triggered_by TEXT,      -- 'github-actions', 'orchestrator'
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

-- State: Replicated from GitHub Actions
CREATE TABLE state_variables (
  name TEXT PRIMARY KEY,
  value TEXT,
  updated_at TIMESTAMP
);

-- Health: System metrics snapshots
CREATE TABLE health_metrics (
  timestamp TIMESTAMP PRIMARY KEY,
  service_status TEXT,
  container_statuses JSON,
  issues JSON
);

-- Audit: All actions for compliance
CREATE TABLE audit_log (
  id INTEGER PRIMARY KEY,
  timestamp TIMESTAMP,
  action TEXT,
  actor TEXT,             -- 'api', 'orchestrator', 'github-actions'
  result TEXT             -- 'success', 'failure'
);
```

## Environment Variables

```bash
# Required
GITHUB_TOKEN=ghp_xxx
GITHUB_REPOSITORY=your-org/tailpaste

# Optional
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR
ORCHESTRATION_DB_PATH=/data/state/orchestration.db
ORCHESTRATION_LOG_PATH=/data/logs
API_WORKERS=4
API_TIMEOUT=120
```

## File Locations

```
/opt/tailpaste/
  ├── docker-compose.orchestration.yml    # Deployment
  ├── Dockerfile.orchestration             # Container image
  ├── requirements-orchestration.txt       # Dependencies
  ├── orchestration/
  │   ├── __init__.py
  │   ├── api_server.py                   # Flask API
  │   ├── state_store.py                  # SQLite interface
  │   ├── init_db.py                      # Schema init
  │   └── worker.py                       # APScheduler
  └── docs/
      ├── CONTAINERIZED_CICD.md            # Architecture
      ├── CONTAINERIZED_CICD_SETUP.md      # Setup guide
      ├── ORCHESTRATION_IMPLEMENTATION.md  # Summary
      └── ORCHESTRATION_GITHUB_ACTIONS.md  # Integration examples

/data/
  ├── state/
  │   └── orchestration.db                 # Main database
  ├── logs/
  │   └── *.log                            # Container logs
  └── artifacts/
      └── build-outputs/                   # Build artifacts
```

## Performance Tuning

```bash
# Increase API concurrency
# Edit docker-compose.orchestration.yml:
api:
  environment:
    API_WORKERS: 8  # Default: 4

# Increase timeout for long jobs
api:
  environment:
    API_TIMEOUT: 300  # Default: 120 seconds

# Vacuum database to optimize
docker-compose -f docker-compose.orchestration.yml exec api \
  sqlite3 /data/state/orchestration.db "VACUUM;"
```

## Key Files Changed

```
NEW:
  - orchestration/*.py (5 modules)
  - Dockerfile.orchestration
  - docker-compose.orchestration.yml
  - requirements-orchestration.txt
  - docs/CONTAINERIZED_CICD*.md (3 files)

TO UPDATE:
  - .github/workflows/*.yml (integrate API calls)
```

## Support

**Documentation**:
- Architecture: See `docs/CONTAINERIZED_CICD.md`
- Setup: See `docs/CONTAINERIZED_CICD_SETUP.md`
- GitHub Actions: See `docs/ORCHESTRATION_GITHUB_ACTIONS.md`
- Summary: See `docs/ORCHESTRATION_IMPLEMENTATION.md`

**Debugging**:
1. Check logs: `docker-compose -f docker-compose.orchestration.yml logs -f`
2. Query DB: `docker-compose ... exec api sqlite3 /data/state/orchestration.db`
3. Test API: `curl http://plex.tailnet:5000/api/health/status`
4. SSH to plex for hands-on debugging

**On Develop Branch**: Branch `develop` contains all code, ready for testing before merge to `main`.
