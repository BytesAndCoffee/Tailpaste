#!/bin/bash
# Quick Reference - Container Crash Diagnostics
# Copy/paste these commands when your container dies

# ==============================================================================
# IMMEDIATE: Check why it crashed
# ==============================================================================

# 1. Is it even running?
docker ps -a | grep tailpaste

# 2. Why did it stop?
docker inspect tailpaste --format='Exit Code: {{.State.ExitCode}}
OOMKilled: {{.State.OOMKilled}}
Error: {{.State.Error}}'

# 3. See the crash in logs
docker logs --tail 50 tailpaste

# 4. Run full diagnostic
./scripts/diagnose-container.sh

# ==============================================================================
# COMMON CRASH SCENARIOS
# ==============================================================================

# SCENARIO: Memory Limit Exceeded (Exit Code 137)
# ────────────────────────────────────────────────
# Solution: Increase memory in docker-compose.yml
# Then restart:
docker-compose down
docker-compose up -d

# SCENARIO: Database Lock Error
# ──────────────────────────────
# Check if volume is corrupt:
ls -la storage/pastes.db*
# If .db-journal exists, delete it and restart:
rm -f storage/pastes.db-journal
docker-compose restart

# SCENARIO: Port 8080 Already in Use
# ────────────────────────────────────
# Check what's using it:
lsof -i :8080
# Kill the process or change port in docker-compose.yml

# SCENARIO: Permission Denied on /data
# ──────────────────────────────────────
chmod 777 storage/
docker-compose down
docker-compose up -d

# ==============================================================================
# MONITORING & LOGGING
# ==============================================================================

# Watch logs in real-time
docker logs -f tailpaste

# Get last 20 app crash details
ls -lt logs/app-*.log | head -5 | awk '{print $NF}' | xargs tail -20

# Copy all logs for analysis
docker cp tailpaste:/var/log/tailpaste ./backup-logs-$(date +%s)/

# Watch container continuously
./scripts/monitor-container.sh

# ==============================================================================
# DEBUGGING
# ==============================================================================

# SSH into container
docker exec -it tailpaste /bin/sh

# Inside container, check app status manually
python /app/main.py

# Check Python dependencies
python -c "import flask, requests; print('Dependencies OK')"

# View system resources
free -h
df -h storage/

# ==============================================================================
# RESTART & RESET
# ==============================================================================

# Quick restart
docker-compose restart tailpaste

# Full rebuild
docker-compose build
docker-compose up -d

# Hard reset (WARNING: deletes container)
docker-compose down
rm -rf logs/*
docker-compose up -d

# ==============================================================================
# RESOURCE MONITORING
# ==============================================================================

# Current memory usage
docker stats tailpaste --no-stream

# Check limits
docker inspect tailpaste --format='Memory: {{.HostConfig.Memory}} bytes
CPUs: {{.HostConfig.CpuQuota}}'

# ==============================================================================
# HEALTH CHECK STATUS
# ==============================================================================

docker inspect tailpaste --format='Health: {{.State.Health.Status}}
Last Check: {{json .State.Health.Log | index . -1}}'

# ==============================================================================
# HELP
# ==============================================================================

# For detailed guide:
cat docs/CONTAINER_DEBUGGING.md

# For summary:
cat CRASH_DIAGNOSTICS.md
