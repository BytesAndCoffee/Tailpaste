# Local CI/CD Orchestration Setup Guide

## Quick Start

### Prerequisites

- `plex` Tailscale host with Docker and Docker Compose installed
- Git access to Tailpaste repository
- 2GB+ available disk space

### Setup on plex

```bash
# 1. Clone or pull repository
cd /opt/tailpaste
git clone https://github.com/your-org/tailpaste.git
cd tailpaste
git checkout develop

# 2. Create data directories
mkdir -p /data/state /data/logs /data/artifacts
chmod 755 /data/state /data/logs /data/artifacts

# 3. Build orchestration images
docker-compose -f docker-compose.orchestration.yml build

# 4. Initialize database
docker-compose -f docker-compose.orchestration.yml run --rm database-init

# 5. Start containers
docker-compose -f docker-compose.orchestration.yml up -d

# 6. Verify all containers are running
docker-compose -f docker-compose.orchestration.yml ps

# 7. Check API health
curl http://plex.tailnet:5000/api/health/status
```

### Expected Output

```
NAME                           STATUS
tailpaste-cicd-api             Up (healthy)
tailpaste-cicd-orchestrator    Up
tailpaste-cicd-health-monitor  Up
```

## Architecture Overview

```
GitHub Actions (Control Plane)
         ↓
    HTTP/REST
         ↓
API Container (Port 5000)
    ├─ Receives triggers
    ├─ Manages jobs
    └─ Returns status
         ↓
    SQLite State DB
    (Durable storage)
         ↓
Orchestrator + Health Monitor
    ├─ Monitor workflow health
    ├─ Enforce dependencies
    └─ Trigger recovery
```

## Configuration

### Environment Variables

Create `.env` file in repository root:

```bash
# GitHub integration
GITHUB_TOKEN=ghp_xxx...
GITHUB_REPOSITORY=your-org/tailpaste

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# Optional: Custom database path
ORCHESTRATION_DB_PATH=/data/state/orchestration.db
```

Load variables:
```bash
docker-compose -f docker-compose.orchestration.yml --env-file .env up -d
```

## Usage Examples

### Trigger CI Workflow

```bash
curl -X POST http://plex.tailnet:5000/api/trigger/ci \
  -H "Content-Type: application/json" \
  -d '{
    "commit": "abc123def456",
    "branch": "develop",
    "python_versions": ["3.10", "3.11", "3.12"],
    "github_run_id": "123456789"
  }'
```

**Response:**
```json
{
  "job_id": "ci-a1b2c3d4",
  "status": "queued",
  "message": "CI workflow queued"
}
```

### Check Job Status

```bash
curl http://plex.tailnet:5000/api/job/ci-a1b2c3d4
```

**Response:**
```json
{
  "id": "ci-a1b2c3d4",
  "type": "ci",
  "status": "running",
  "commit": "abc123def456",
  "branch": "develop",
  "started_at": "2026-01-27T10:15:00",
  "created_at": "2026-01-27T10:14:30",
  "updated_at": "2026-01-27T10:14:45"
}
```

### List Recent Jobs

```bash
# All jobs
curl http://plex.tailnet:5000/api/admin/jobs

# Filter by status
curl "http://plex.tailnet:5000/api/admin/jobs?status=running"

# Filter by type
curl "http://plex.tailnet:5000/api/admin/jobs?type=ci&limit=10"
```

### Get All State Variables

```bash
curl http://plex.tailnet:5000/api/state
```

### View Audit Log

```bash
curl "http://plex.tailnet:5000/api/admin/audit-log?limit=50"
```

### Trigger Recovery

```bash
curl -X POST http://plex.tailnet:5000/api/recovery/execute \
  -H "Content-Type: application/json" \
  -d '{
    "recovery_action": "restart-service",
    "affected_workflow": "deploy"
  }'
```

### Trigger Rollback

```bash
curl -X POST http://plex.tailnet:5000/api/rollback/execute \
  -H "Content-Type: application/json" \
  -d '{
    "target_version": "v1.2.2",
    "reason": "deployment_failure"
  }'
```

## Monitoring & Debugging

### View Logs

```bash
# All containers
docker-compose -f docker-compose.orchestration.yml logs -f

# Specific service
docker-compose -f docker-compose.orchestration.yml logs -f api
docker-compose -f docker-compose.orchestration.yml logs -f orchestrator
docker-compose -f docker-compose.orchestration.yml logs -f health-monitor

# Last 100 lines
docker-compose -f docker-compose.orchestration.yml logs --tail 100 api
```

### Access SQLite Database

```bash
# Connect to database
docker-compose -f docker-compose.orchestration.yml exec api sqlite3 /data/state/orchestration.db

# List tables
> .tables

# Show recent jobs
> SELECT id, type, status, created_at FROM jobs ORDER BY created_at DESC LIMIT 10;

# Show workflow dependencies
> SELECT * FROM workflow_dependencies;

# Show health metrics
> SELECT * FROM health_metrics ORDER BY timestamp DESC LIMIT 5;

# Show audit log
> SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 20;

# Exit
> .quit
```

### Container Status

```bash
# Check container health
docker-compose -f docker-compose.orchestration.yml ps

# Inspect specific container
docker inspect tailpaste-cicd-api

# View resource usage
docker stats tailpaste-cicd-api
```

### Restart Containers

```bash
# Restart one container
docker-compose -f docker-compose.orchestration.yml restart api

# Restart all
docker-compose -f docker-compose.orchestration.yml restart

# Stop all
docker-compose -f docker-compose.orchestration.yml down

# Start all
docker-compose -f docker-compose.orchestration.yml up -d
```

## Data Persistence

### Backup State Database

```bash
# Manual backup
docker-compose -f docker-compose.orchestration.yml exec api \
  sqlite3 /data/state/orchestration.db \
  ".backup /data/state/orchestration.backup.db"

# Or copy volume
docker run --rm -v cicd-state:/data/state -v $(pwd):/backup \
  busybox cp /data/state/orchestration.db /backup/orchestration.db

# Schedule daily backup (on plex host)
0 2 * * * docker run --rm -v cicd-state:/data/state -v /backups/tailpaste:/backup busybox cp /data/state/orchestration.db /backup/orchestration.$(date +\%Y\%m\%d).db
```

### Restore from Backup

```bash
docker-compose -f docker-compose.orchestration.yml down
docker volume rm cicd-state
docker volume create cicd-state
docker run --rm -v cicd-state:/data/state -v $(pwd):/backup \
  busybox cp /backup/orchestration.db /data/state/orchestration.db
docker-compose -f docker-compose.orchestration.yml up -d
```

## Troubleshooting

### API Health Check Failing

```bash
# Check API logs
docker-compose -f docker-compose.orchestration.yml logs api

# Test manually
curl -v http://localhost:5000/api/health/status

# Check if port is bound
lsof -i :5000
```

### Database Lock Errors

```bash
# Check for long-running queries
docker-compose -f docker-compose.orchestration.yml exec api sqlite3 /data/state/orchestration.db \
  "PRAGMA database_list;"

# If corrupted, reinitialize
docker-compose -f docker-compose.orchestration.yml down
docker volume rm cicd-state
docker-compose -f docker-compose.orchestration.yml build
docker-compose -f docker-compose.orchestration.yml run --rm database-init
docker-compose -f docker-compose.orchestration.yml up -d
```

### Containers Not Starting

```bash
# Check docker daemon
sudo systemctl status docker

# Check logs
docker-compose -f docker-compose.orchestration.yml logs

# Rebuild images
docker-compose -f docker-compose.orchestration.yml build --no-cache

# Retry startup
docker-compose -f docker-compose.orchestration.yml up -d
```

## Performance Tuning

### Increase API Workers

Edit `docker-compose.orchestration.yml`:
```yaml
api:
  environment:
    API_WORKERS: 8  # Increase from 4
```

Then restart:
```bash
docker-compose -f docker-compose.orchestration.yml up -d
```

### Database Optimization

```bash
# Vacuum database to reclaim space
docker-compose -f docker-compose.orchestration.yml exec api sqlite3 \
  /data/state/orchestration.db \
  "VACUUM;"

# Analyze for query optimization
docker-compose -f docker-compose.orchestration.yml exec api sqlite3 \
  /data/state/orchestration.db \
  "ANALYZE;"
```

### Monitor Disk Usage

```bash
# Check volume size
docker volume inspect cicd-state

# Check logs volume
du -sh /var/lib/docker/volumes/cicd-logs/_data

# Cleanup old logs (> 30 days)
find /var/lib/docker/volumes/cicd-logs/_data -type f -mtime +30 -delete
```

## Integration with GitHub Actions

See [CONTAINERIZED_CICD.md](CONTAINERIZED_CICD.md) for detailed workflow integration examples.

## Support & Issues

For issues or questions:
1. Check logs: `docker-compose -f docker-compose.orchestration.yml logs -f`
2. Query database: `docker-compose -f docker-compose.orchestration.yml exec api sqlite3 /data/state/orchestration.db`
3. Test API endpoints manually with curl
4. Check plex host resources: `docker stats`
