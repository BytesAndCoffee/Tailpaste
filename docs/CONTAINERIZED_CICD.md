# Containerized CI/CD Orchestration

## Architecture Overview

This document describes the containerized CI/CD orchestration system that runs locally on the `plex` Tailscale host. GitHub Actions serves as the lightweight control plane, while actual execution and state management happen in containers with durable SQLite storage.

### Design Philosophy

- **GitHub Actions = Control Plane**: Minimal workflows that trigger operations and report results
- **plex Host = Execution Plane**: Containers manage workflows, maintain state, coordinate between systems
- **SQLite = State Store**: Durable, queryable state for build/test/deploy/health tracking
- **Local Execution**: All heavy lifting happens on trusted hardware with full access to Tailscale network

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Actions (Control)                     │
│                                                                  │
│  CI.yml → POST /api/trigger/ci                                 │
│  Deploy.yml → POST /api/trigger/deploy                         │
│  Health-Check.yml → GET /api/health/status                     │
│  Recovery.yml → POST /api/recovery/execute                     │
│  Rollback.yml → POST /api/rollback/execute                     │
└──────────────────────┬────────────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          │            │            │
          ↓            ↓            ↓
    ┌──────────┐  ┌──────────┐  ┌──────────────┐
    │   plex   │  │   plex   │  │    plex      │
    │   Host   │  │   Host   │  │    Host      │
    │ ────────│  │────────── │  │──────────────│
    │ Durable  │  │ Durable  │  │  Durable     │
    │ SQLite   │  │ SQLite   │  │  SQLite      │
    └──────────┘  └──────────┘  └──────────────┘
          ▲              ▲              ▲
          │              │              │
    ┌─────────────────────────────────────┐
    │    docker-compose.yml on plex       │
    │                                     │
    │  api:                               │
    │    - Flask REST API server          │
    │    - Executes scripts/workflows     │
    │    - Manages state transitions      │
    │    - Port 5000 (via tailscale)      │
    │                                     │
    │  orchestrator:                      │
    │    - Monitors workflow health       │
    │    - Enforces dependencies          │
    │    - Recovers from failures         │
    │    - Runs on schedule               │
    │                                     │
    │  health-monitor:                    │
    │    - Checks container/app health    │
    │    - Updates state DB               │
    │    - Triggers alerts                │
    │                                     │
    │  volumes:                           │
    │    - cicd-state: /data/state        │
    │    - logs: /data/logs               │
    │                                     │
    └─────────────────────────────────────┘
```

## Key Components

### 1. API Container (`api`)

**Purpose**: REST API endpoint for GitHub Actions to interact with the orchestration system.

**Responsibilities**:
- Receive workflow trigger requests from GitHub Actions
- Execute CI/test/deploy scripts in controlled environment
- Manage workflow state transitions
- Return results and status to GitHub Actions
- Maintain audit logs of all operations

**Endpoints**:
```
POST /api/trigger/ci
  - Body: { "commit": "abc123", "branch": "main", "python_versions": ["3.10", "3.11", "3.12"] }
  - Returns: { "job_id": "xyz", "status": "queued" }

POST /api/trigger/integration-tests
  - Body: { "commit": "abc123", "python_version": "3.11" }
  - Returns: { "job_id": "xyz", "status": "queued" }

POST /api/trigger/deploy
  - Body: { "version": "v1.2.3", "environment": "production" }
  - Returns: { "job_id": "xyz", "status": "queued" }

POST /api/recovery/execute
  - Body: { "recovery_action": "restart-service", "affected_workflow": "deploy" }
  - Returns: { "recovery_id": "xyz", "status": "in_progress" }

POST /api/rollback/execute
  - Body: { "target_version": "v1.2.2", "reason": "deployment_failure" }
  - Returns: { "rollback_id": "xyz", "status": "in_progress" }

GET /api/health/status
  - Returns: { "status": "healthy", "checks": {...}, "timestamp": "2026-01-27T..." }

GET /api/job/{job_id}
  - Returns: { "status": "running", "progress": 45, "logs": [...] }

GET /api/state
  - Returns: Complete state snapshot for GitHub Actions variables

POST /api/sync-variables
  - Body: { "variables": { "KEY": "VALUE" } }
  - Syncs state to GitHub via gh CLI
```

**Technology**:
- Flask + Gunicorn
- Python 3.11 (matches main Tailpaste version)
- requests-unixsocket for Tailscale LocalAPI (inherited from Tailpaste)
- SQLAlchemy for state management

### 2. Orchestrator Container (`orchestrator`)

**Purpose**: Manages workflow scheduling, dependency tracking, and failure recovery.

**Responsibilities**:
- Monitor workflow states in SQLite database
- Enforce workflow dependency chains
- Detect stuck or failed workflows
- Trigger recovery procedures
- Maintain health metrics and reports
- Communicate with API container for coordination

**Scheduled Tasks**:
- Every 5 minutes: Health check + state consistency validation
- Every 15 minutes: Workflow orchestration + dependency validation
- Every 30 minutes: Cleanup old jobs + archive logs
- Daily: Generate comprehensive reports

**Technology**:
- APScheduler for scheduling
- SQLite3 for persistent state
- Python 3.11
- Existing `WorkflowStatusMonitor` and `OrchestrationHelper` classes

### 3. Health Monitor Container (`health-monitor`)

**Purpose**: Track application and infrastructure health.

**Responsibilities**:
- Monitor Tailpaste service availability
- Check database integrity and size
- Verify Tailscale connectivity
- Track container resource usage
- Auto-recover from detected failures
- Update health metrics in state DB

**Checks** (every 5 minutes):
- HTTP endpoint availability
- SQLite database health
- Disk usage
- Container status
- Tailscale connectivity

**Technology**:
- Existing `health_check.py` script
- APScheduler for scheduling
- SQLite for metrics storage

### 4. State Database (Durable SQLite)

**Schema**:
```sql
-- Jobs/Runs tracking
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,  -- 'ci', 'integration', 'deploy', 'recovery', 'rollback'
    commit TEXT,
    version TEXT,
    status TEXT NOT NULL,  -- 'queued', 'running', 'success', 'failure', 'recovered'
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    triggered_by TEXT,  -- 'github-actions', 'orchestrator', 'health-monitor'
    environment TEXT,  -- 'test', 'staging', 'production'
    metadata JSON,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- Workflow dependencies and sequencing
CREATE TABLE workflow_dependencies (
    workflow TEXT PRIMARY KEY,
    depends_on TEXT,  -- CSV list
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- State variables (replicated from GitHub)
CREATE TABLE state_variables (
    name TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    source TEXT,  -- 'api', 'orchestrator', 'github-actions'
    synced_at TIMESTAMP,
    updated_at TIMESTAMP NOT NULL
);

-- Health metrics
CREATE TABLE health_metrics (
    timestamp TIMESTAMP PRIMARY KEY,
    service_status TEXT,
    database_size_mb REAL,
    disk_usage_percent REAL,
    container_statuses JSON,
    tailscale_connected BOOLEAN,
    issues JSON
);

-- Audit log
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP NOT NULL,
    action TEXT NOT NULL,
    actor TEXT,  -- 'api', 'orchestrator', 'health-monitor'
    details JSON,
    result TEXT  -- 'success', 'failure'
);
```

## Deployment

### Prerequisites on plex

1. Docker and Docker Compose installed
2. Tailscale client configured
3. Access to Tailpaste repository
4. Minimum 2GB disk space for SQLite + logs

### Setup Steps

```bash
# 1. Clone repository on plex
cd /opt/tailpaste
git clone https://github.com/your-org/tailpaste.git
cd tailpaste

# 2. Check out develop branch
git checkout develop

# 3. Create data directories
mkdir -p /data/state /data/logs
chmod 755 /data/state /data/logs

# 4. Initialize SQLite database
docker-compose -f docker-compose.orchestration.yml run api python init_db.py

# 5. Build and start containers
docker-compose -f docker-compose.orchestration.yml build
docker-compose -f docker-compose.orchestration.yml up -d

# 6. Verify containers are running
docker-compose -f docker-compose.orchestration.yml ps

# 7. Test API
curl http://plex.tailnet:5000/api/health/status

# 8. Configure GitHub Actions workflows to call API
# Update .github/workflows/*.yml to use:
# - curl -X POST http://plex.tailnet:5000/api/trigger/ci
# - curl -X GET http://plex.tailnet:5000/api/job/{job_id}
```

### GitHub Actions Integration

Update workflow files to call the API instead of using self-hosted runners:

```yaml
# .github/workflows/ci.yml (simplified)
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  trigger-ci:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger orchestration system
        run: |
          curl -X POST http://plex.tailnet:5000/api/trigger/ci \
            -H "Content-Type: application/json" \
            -d '{
              "commit": "${{ github.sha }}",
              "branch": "${{ github.ref_name }}",
              "python_versions": ["3.10", "3.11", "3.12"],
              "github_run_id": "${{ github.run_id }}"
            }'
```

## Monitoring & Debugging

### View Logs

```bash
# All containers
docker-compose -f docker-compose.orchestration.yml logs -f

# Specific container
docker-compose -f docker-compose.orchestration.yml logs -f api
docker-compose -f docker-compose.orchestration.yml logs -f orchestrator
docker-compose -f docker-compose.orchestration.yml logs -f health-monitor

# Last 100 lines
docker-compose -f docker-compose.orchestration.yml logs --tail=100 api
```

### Access SQLite State

```bash
# Connect to database
docker-compose -f docker-compose.orchestration.yml exec api sqlite3 /data/state/orchestration.db

# Example queries
> SELECT id, type, status, created_at FROM jobs ORDER BY created_at DESC LIMIT 10;
> SELECT * FROM state_variables;
> SELECT * FROM health_metrics ORDER BY timestamp DESC LIMIT 5;
```

### Restart Containers

```bash
# Restart orchestrator (maintains state)
docker-compose -f docker-compose.orchestration.yml restart orchestrator

# Restart API (drops in-flight requests)
docker-compose -f docker-compose.orchestration.yml restart api

# Full restart
docker-compose -f docker-compose.orchestration.yml down
docker-compose -f docker-compose.orchestration.yml up -d
```

## Migration Path

### Phase 1: Parallel Operation (Weeks 1-2)

- Deploy containerized orchestration on plex
- GitHub Actions workflows run both old and new systems
- Validate that state stays consistent
- Test recovery and rollback procedures

### Phase 2: Cutover (Week 3)

- Disable old self-hosted runners for CI/test/deploy
- Redirect all workflow triggers to API
- Monitor for issues
- Keep rollback procedure ready

### Phase 3: Cleanup (Week 4)

- Remove GitHub Actions self-hosted runner configuration
- Archive old scripts (keep for reference)
- Document lessons learned
- Optimize containerized system based on production usage

## Advantages of This Approach

✅ **Reliable State Management**: Persistent SQLite replaces fragile GitHub variables  
✅ **Local Control**: Full transparency and debugging on plex host  
✅ **Scalable**: Can add more containers if needed (separate orchestrators, monitors)  
✅ **Minimal GitHub Actions**: Control plane is lightweight, maintainable  
✅ **Fast Feedback**: No network latency for job execution  
✅ **Tailscale Native**: Inherited security model, no external APIs needed  
✅ **Cost**: No paid GitHub Actions runners, no cloud infrastructure  
✅ **Recovery**: Deterministic, can replay failed jobs from state DB  

## Challenges & Mitigations

| Challenge | Mitigation |
|-----------|-----------|
| Single point of failure on plex | Regular backups to cloud, monitoring alerts |
| GitHub Actions network delays | Acceptable, control plane is simple |
| State inconsistency | SQLite + audit log, reconciliation procedures |
| Debugging containerized workflows | Mount source code as volume, access shell |
| Disk space for logs | Automatic cleanup, 30-day retention |
| Container crashes | Health monitor detects, auto-restart via docker |

## Next Steps

1. Create `Dockerfile.orchestration` with all dependencies
2. Create `docker-compose.orchestration.yml` for plex deployment
3. Implement API container with Flask endpoints
4. Migrate `WorkflowStatusMonitor` to orchestrator container
5. Create SQLite schema and initialization script
6. Update GitHub Actions workflows to use API
7. Test end-to-end on develop branch
8. Document operational procedures

