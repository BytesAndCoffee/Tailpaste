# GitHub Actions Integration Examples

This document shows how to update GitHub Actions workflows to use the containerized CI/CD orchestration system running on plex.

## Overview

Instead of running tests/builds directly in GitHub Actions, workflows now:
1. Call the API to queue a job on plex
2. Poll the API to check job status
3. Report results back to GitHub

This keeps GitHub Actions as a thin control plane while all heavy lifting happens locally on plex.

## Configuration

Set these secrets/variables in GitHub repository settings:

### Repository Secrets
```
ORCHESTRATION_API_URL    # http://plex.tailnet:5000
GITHUB_TOKEN             # (already available in actions)
```

### Repository Variables (optional)
```
ORCHESTRATION_TIMEOUT    # 3600 (seconds)
ORCHESTRATION_POLL_INTERVAL  # 10 (seconds)
```

## Pattern: Queue Job + Poll Status

All workflows follow this pattern:

```yaml
- name: Queue CI job
  id: queue
  run: |
    RESPONSE=$(curl -X POST ${{ secrets.ORCHESTRATION_API_URL }}/api/trigger/ci \
      -H "Content-Type: application/json" \
      -d '{
        "commit": "${{ github.sha }}",
        "branch": "${{ github.ref_name }}",
        "python_versions": ["3.10", "3.11", "3.12"],
        "github_run_id": "${{ github.run_id }}"
      }')
    
    JOB_ID=$(echo "$RESPONSE" | jq -r '.job_id')
    echo "job_id=$JOB_ID" >> $GITHUB_OUTPUT
    echo "Queued job: $JOB_ID"

- name: Poll job status
  id: poll
  run: |
    JOB_ID="${{ steps.queue.outputs.job_id }}"
    TIMEOUT=${{ vars.ORCHESTRATION_TIMEOUT || 3600 }}
    INTERVAL=${{ vars.ORCHESTRATION_POLL_INTERVAL || 10 }}
    ELAPSED=0
    
    while [ $ELAPSED -lt $TIMEOUT ]; do
      STATUS=$(curl -s ${{ secrets.ORCHESTRATION_API_URL }}/api/job/$JOB_ID | jq -r '.status')
      
      case "$STATUS" in
        success)
          echo "Job succeeded: $JOB_ID"
          echo "status=success" >> $GITHUB_OUTPUT
          exit 0
          ;;
        failure|recovered)
          echo "Job failed: $JOB_ID (status: $STATUS)"
          echo "status=failure" >> $GITHUB_OUTPUT
          exit 1
          ;;
        running|queued)
          echo "Job status: $STATUS (elapsed: ${ELAPSED}s)"
          sleep $INTERVAL
          ELAPSED=$((ELAPSED + INTERVAL))
          ;;
        *)
          echo "Unknown status: $STATUS"
          exit 2
          ;;
      esac
    done
    
    echo "Job timeout: $JOB_ID"
    exit 1

- name: Report status
  if: always()
  run: |
    JOB_ID="${{ steps.queue.outputs.job_id }}"
    STATUS="${{ steps.poll.outputs.status }}"
    echo "Job $JOB_ID completed with status: $STATUS"
```

## Example 1: CI Workflow

**File**: `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]
  workflow_dispatch:

env:
  ORCHESTRATION_API_URL: http://plex.tailnet:5000

jobs:
  trigger-ci:
    name: Trigger CI on plex
    runs-on: ubuntu-latest
    outputs:
      job_id: ${{ steps.queue.outputs.job_id }}
      status: ${{ steps.poll.outputs.status }}
    
    steps:
      - name: Queue CI job
        id: queue
        run: |
          RESPONSE=$(curl -s -X POST $ORCHESTRATION_API_URL/api/trigger/ci \
            -H "Content-Type: application/json" \
            -d '{
              "commit": "${{ github.sha }}",
              "branch": "${{ github.ref_name }}",
              "python_versions": ["3.10", "3.11", "3.12"],
              "github_run_id": "${{ github.run_id }}"
            }')
          
          if [ $? -ne 0 ]; then
            echo "Failed to queue job"
            echo "$RESPONSE"
            exit 1
          fi
          
          JOB_ID=$(echo "$RESPONSE" | jq -r '.job_id')
          echo "job_id=$JOB_ID" >> $GITHUB_OUTPUT
          echo "✓ Queued job: $JOB_ID"

      - name: Poll job status
        id: poll
        run: |
          JOB_ID="${{ steps.queue.outputs.job_id }}"
          TIMEOUT=3600
          INTERVAL=10
          ELAPSED=0
          
          echo "Polling job status (timeout: ${TIMEOUT}s, interval: ${INTERVAL}s)..."
          
          while [ $ELAPSED -lt $TIMEOUT ]; do
            RESPONSE=$(curl -s $ORCHESTRATION_API_URL/api/job/$JOB_ID)
            STATUS=$(echo "$RESPONSE" | jq -r '.status // "unknown"')
            
            case "$STATUS" in
              success)
                echo "✓ Job succeeded: $JOB_ID"
                echo "status=success" >> $GITHUB_OUTPUT
                exit 0
                ;;
              failure)
                echo "✗ Job failed: $JOB_ID"
                echo "$RESPONSE" | jq '.'
                echo "status=failure" >> $GITHUB_OUTPUT
                exit 1
                ;;
              running|queued)
                printf "."
                sleep $INTERVAL
                ELAPSED=$((ELAPSED + INTERVAL))
                ;;
              *)
                echo "? Unknown status: $STATUS"
                echo "$RESPONSE" | jq '.'
                exit 2
                ;;
            esac
          done
          
          echo "✗ Job timeout"
          exit 1

      - name: Summary
        if: always()
        run: |
          cat << EOF >> $GITHUB_STEP_SUMMARY
          ## CI Job Results
          - **Job ID**: ${{ steps.queue.outputs.job_id }}
          - **Status**: ${{ steps.poll.outputs.status }}
          - **API**: $ORCHESTRATION_API_URL/api/job/${{ steps.queue.outputs.job_id }}
          EOF

  # Downstream jobs depend on CI success
  notify-success:
    needs: trigger-ci
    if: success()
    runs-on: ubuntu-latest
    steps:
      - name: CI passed
        run: echo "✓ CI job passed, proceeding to integration tests"

  notify-failure:
    needs: trigger-ci
    if: failure()
    runs-on: ubuntu-latest
    steps:
      - name: CI failed
        run: |
          echo "✗ CI job failed"
          exit 1
```

## Example 2: Integration Tests Workflow

**File**: `.github/workflows/integration-test.yml`

```yaml
name: Integration Tests

on:
  workflow_run:
    workflows: [CI]
    types: [completed]
    branches: [main, develop]
  workflow_dispatch:

env:
  ORCHESTRATION_API_URL: http://plex.tailnet:5000

jobs:
  check-ci-status:
    runs-on: ubuntu-latest
    outputs:
      should_run: ${{ steps.check.outputs.should_run }}
    steps:
      - name: Check CI status
        id: check
        run: |
          if [ "${{ github.event.workflow_run.conclusion }}" == "success" ]; then
            echo "should_run=true" >> $GITHUB_OUTPUT
          else
            echo "should_run=false" >> $GITHUB_OUTPUT
          fi

  trigger-integration-tests:
    needs: check-ci-status
    if: needs.check-ci-status.outputs.should_run == 'true'
    runs-on: ubuntu-latest
    steps:
      - name: Queue integration tests
        id: queue
        run: |
          RESPONSE=$(curl -s -X POST $ORCHESTRATION_API_URL/api/trigger/integration-tests \
            -H "Content-Type: application/json" \
            -d '{
              "commit": "${{ github.sha }}",
              "python_version": "3.11",
              "github_run_id": "${{ github.run_id }}"
            }')
          
          JOB_ID=$(echo "$RESPONSE" | jq -r '.job_id')
          echo "job_id=$JOB_ID" >> $GITHUB_OUTPUT
          echo "✓ Queued integration tests: $JOB_ID"

      - name: Poll test status
        id: poll
        run: |
          JOB_ID="${{ steps.queue.outputs.job_id }}"
          TIMEOUT=1800
          INTERVAL=15
          ELAPSED=0
          
          while [ $ELAPSED -lt $TIMEOUT ]; do
            STATUS=$(curl -s $ORCHESTRATION_API_URL/api/job/$JOB_ID | jq -r '.status')
            
            if [ "$STATUS" == "success" ]; then
              echo "✓ Integration tests passed"
              exit 0
            elif [ "$STATUS" == "failure" ]; then
              echo "✗ Integration tests failed"
              exit 1
            fi
            
            sleep $INTERVAL
            ELAPSED=$((ELAPSED + INTERVAL))
          done
          
          echo "✗ Tests timed out"
          exit 1
```

## Example 3: Deploy Workflow

**File**: `.github/workflows/deploy.yml`

```yaml
name: Deploy

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to deploy'
        required: true
      environment:
        description: 'Environment'
        required: true
        default: 'staging'
        type: choice
        options:
          - staging
          - production

env:
  ORCHESTRATION_API_URL: http://plex.tailnet:5000

jobs:
  trigger-deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Determine version
        id: version
        run: |
          if [ -n "${{ github.ref_name }}" ]; then
            VERSION=${{ github.ref_name }}
          else
            VERSION=${{ github.event.inputs.version }}
          fi
          
          ENVIRONMENT=${{ github.event.inputs.environment || 'staging' }}
          echo "version=$VERSION" >> $GITHUB_OUTPUT
          echo "environment=$ENVIRONMENT" >> $GITHUB_OUTPUT

      - name: Queue deployment
        id: queue
        run: |
          VERSION="${{ steps.version.outputs.version }}"
          ENVIRONMENT="${{ steps.version.outputs.environment }}"
          
          RESPONSE=$(curl -s -X POST $ORCHESTRATION_API_URL/api/trigger/deploy \
            -H "Content-Type: application/json" \
            -d "{
              \"version\": \"$VERSION\",
              \"environment\": \"$ENVIRONMENT\",
              \"github_run_id\": \"${{ github.run_id }}\"
            }")
          
          JOB_ID=$(echo "$RESPONSE" | jq -r '.job_id')
          echo "job_id=$JOB_ID" >> $GITHUB_OUTPUT
          echo "✓ Queued deployment: $JOB_ID"

      - name: Monitor deployment
        id: monitor
        run: |
          JOB_ID="${{ steps.queue.outputs.job_id }}"
          TIMEOUT=3600
          INTERVAL=30
          ELAPSED=0
          
          while [ $ELAPSED -lt $TIMEOUT ]; do
            RESPONSE=$(curl -s $ORCHESTRATION_API_URL/api/job/$JOB_ID)
            STATUS=$(echo "$RESPONSE" | jq -r '.status')
            
            if [ "$STATUS" == "success" ]; then
              echo "✓ Deployment succeeded"
              echo "$RESPONSE" | jq '.'
              exit 0
            elif [ "$STATUS" == "failure" ]; then
              echo "✗ Deployment failed"
              echo "$RESPONSE" | jq '.'
              exit 1
            fi
            
            echo "Status: $STATUS (elapsed: ${ELAPSED}s)"
            sleep $INTERVAL
            ELAPSED=$((ELAPSED + INTERVAL))
          done
          
          echo "✗ Deployment timed out"
          exit 1

      - name: Notify deployment
        if: always()
        run: |
          cat << EOF >> $GITHUB_STEP_SUMMARY
          ## Deployment Summary
          - **Version**: ${{ steps.version.outputs.version }}
          - **Environment**: ${{ steps.version.outputs.environment }}
          - **Job ID**: ${{ steps.queue.outputs.job_id }}
          - **Status**: ${{ job.status }}
          EOF
```

## Example 4: Health Check Workflow

**File**: `.github/workflows/health-check.yml`

```yaml
name: Health Check

on:
  schedule:
    - cron: '*/5 * * * *'  # Every 5 minutes
  workflow_dispatch:

env:
  ORCHESTRATION_API_URL: http://plex.tailnet:5000

jobs:
  check-system-health:
    runs-on: ubuntu-latest
    steps:
      - name: Check orchestration API
        id: api
        run: |
          RESPONSE=$(curl -s -w "\n%{http_code}" $ORCHESTRATION_API_URL/api/health/status)
          HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
          BODY=$(echo "$RESPONSE" | head -n-1)
          
          if [ "$HTTP_CODE" -eq 200 ]; then
            echo "✓ API is healthy"
            echo "status=healthy" >> $GITHUB_OUTPUT
            echo "$BODY" | jq '.' >> $GITHUB_STEP_SUMMARY
          else
            echo "✗ API returned status: $HTTP_CODE"
            echo "status=unhealthy" >> $GITHUB_OUTPUT
            exit 1
          fi

      - name: Check job queue
        run: |
          JOBS=$(curl -s "$ORCHESTRATION_API_URL/api/admin/jobs?limit=5" | jq '.jobs | length')
          echo "Recent jobs in queue: $JOBS"

      - name: Alert if unhealthy
        if: steps.api.outputs.status != 'healthy'
        run: |
          echo "⚠️ Orchestration system is unhealthy!"
          exit 1
```

## Handling Timeouts and Failures

### Timeout Behavior
```bash
# If job doesn't complete within ORCHESTRATION_TIMEOUT:
# 1. Workflow fails
# 2. Manual investigation required on plex
# 3. Can manually update job status via API
```

### Manual Job Status Update
```bash
# If a job gets stuck, manually update it:
curl -X PATCH http://plex.tailnet:5000/api/job/ci-abc123/status \
  -H "Content-Type: application/json" \
  -d '{
    "status": "success",
    "completed_at": "2026-01-27T15:30:00"
  }'
```

### Recovery Procedures
```bash
# Trigger manual recovery if needed:
curl -X POST http://plex.tailnet:5000/api/recovery/execute \
  -H "Content-Type: application/json" \
  -d '{
    "recovery_action": "restart-service",
    "affected_workflow": "ci"
  }'
```

## Testing Integration

### Test with mock job
```bash
# Create a test job
curl -X POST http://plex.tailnet:5000/api/trigger/ci \
  -H "Content-Type: application/json" \
  -d '{"commit": "test", "branch": "test"}'

# Check status
curl http://plex.tailnet:5000/api/job/ci-test123

# Simulate completion
curl -X PATCH http://plex.tailnet:5000/api/job/ci-test123/status \
  -H "Content-Type: application/json" \
  -d '{"status": "success"}'
```

### GitHub Actions test step
```yaml
- name: Test orchestration API
  run: |
    set -e
    
    # Health check
    curl -f http://plex.tailnet:5000/api/health/status > /dev/null
    echo "✓ Health check passed"
    
    # Queue test job
    RESPONSE=$(curl -s -X POST http://plex.tailnet:5000/api/trigger/ci \
      -H "Content-Type: application/json" \
      -d '{"commit": "test", "branch": "test"}')
    JOB_ID=$(echo "$RESPONSE" | jq -r '.job_id')
    echo "✓ Queued test job: $JOB_ID"
    
    # Query job
    curl -f http://plex.tailnet:5000/api/job/$JOB_ID > /dev/null
    echo "✓ Job query successful"
```

## Migration Checklist

- [ ] Update `.github/workflows/ci.yml` with API calls
- [ ] Update `.github/workflows/integration-test.yml`
- [ ] Update `.github/workflows/deploy.yml`
- [ ] Update `.github/workflows/health-check.yml`
- [ ] Update `.github/workflows/security.yml`
- [ ] Update `.github/workflows/recovery.yml`
- [ ] Set `ORCHESTRATION_API_URL` secret in GitHub
- [ ] Test each workflow in dry-run mode
- [ ] Monitor for issues on develop branch
- [ ] Document any changes for team
- [ ] Disable old self-hosted runners

## Debugging

### Check recent jobs
```bash
curl "http://plex.tailnet:5000/api/admin/jobs?type=ci&limit=20" | jq '.jobs[] | {id, status, created_at}'
```

### View audit log
```bash
curl "http://plex.tailnet:5000/api/admin/audit-log?limit=50" | jq '.entries[] | {timestamp, action, result}'
```

### SSH into plex for hands-on debugging
```bash
ssh inspector@plex.tailnet
docker-compose -f /opt/tailpaste/docker-compose.orchestration.yml logs -f api
```
