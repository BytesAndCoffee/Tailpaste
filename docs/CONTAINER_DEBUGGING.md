# Docker Container Crash Debugging Guide

## Quick Commands to Diagnose Why Your Container is Dying

### 1. **Run the Automated Diagnostic Script**
```bash
./scripts/diagnose-container.sh
```
This gives you a complete overview of the container state, logs, and resource usage.

### 2. **View Real-Time Logs**
```bash
# Watch logs as they happen
docker logs -f tailpaste

# See logs with timestamps
docker logs --timestamps tailpaste

# Get last 100 lines
docker logs --tail 100 tailpaste

# Get logs from the last 5 minutes
docker logs --since 5m tailpaste
```

### 3. **Check Container Exit Status**
```bash
# Full container state including exit code
docker inspect tailpaste | grep -A 20 '"State"'

# Just the exit code
docker inspect tailpaste --format='{{.State.ExitCode}}'

# Why it stopped
docker inspect tailpaste --format='{{.State.Error}}'

# Was it OOMKilled?
docker inspect tailpaste --format='{{.State.OOMKilled}}'
```

### 4. **Check Resource Limits & Usage**
```bash
# Current memory and CPU usage (while running)
docker stats tailpaste --no-stream

# Configured limits
docker inspect tailpaste --format='Memory Limit: {{.HostConfig.Memory}} bytes
CPU Limit: {{.HostConfig.CpuQuota}}'

# Check available system memory
free -h

# Check disk space for /data volume
df -h storage/
```

### 5. **Access Crash Logs Inside Container**
```bash
# View crash logs (enhanced logging from updated entrypoint)
docker exec tailpaste ls -la /var/log/tailpaste/

# View last crash
docker exec tailpaste tail -100 /var/log/tailpaste/app-*.log

# Copy logs to host for analysis
docker cp tailpaste:/var/log/tailpaste ./container-logs/
```

### 6. **Start Container in Debug Mode**
```bash
# Use debug image with extra tools
docker-compose build --target debug

# Run with interactive shell for inspection
docker exec -it tailpaste /bin/sh

# Once inside, useful commands:
ps aux                          # See running processes
free -h                         # Memory usage
df -h                           # Disk usage
cat /var/log/tailpaste/app-*   # View crash logs
python -c "import sys; print(sys.path)"  # Check Python setup
```

## Common Crash Causes & How to Identify Them

### **Exit Code 0**
- Clean exit - check logs for reason
- Likely issues: config error, missing dependencies, unhandled exception
- **Fix**: Review application logs carefully

### **Exit Code 1**
- Generic application error
- Could be: Python exception, missing file, permission error
- **Fix**: Check logs for traceback, verify file permissions on /data

### **Exit Code 137 (SIGKILL)**
- Container was killed by the system
- Most common: Out of Memory (OOMKill)
- Also: Docker daemon restarted, manual kill command
- **Check**: `docker inspect tailpaste --format='{{.State.OOMKilled}}'`
- **Fix**: If OOMKilled=true, increase memory limit in docker-compose.yml

```yaml
deploy:
  resources:
    limits:
      memory: 1G  # Increase from 512M
```

### **Exit Code 143 (SIGTERM)**
- Graceful termination received
- Docker asked container to stop (normal shutdown)
- Could indicate: Host maintenance, container upgrade, timeout
- **Fix**: Normal - may restart automatically due to `restart: unless-stopped`

### **Exit Code 139 (SIGSEGV)**
- Segmentation fault - memory corruption
- Python interpreter crashed
- **Fix**: Check for native library issues, memory leaks in C extensions

## Resource Limits in docker-compose.yml

The updated docker-compose.yml includes:

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'          # Max 2 CPU cores
      memory: 512M         # Max 512MB RAM
    reservations:
      cpus: '0.5'          # Guaranteed 0.5 CPU
      memory: 256M         # Guaranteed 256MB RAM
```

**If container keeps getting OOMKilled:**
- Increase `memory: 512M` → `memory: 1G` or `2G`
- Check what's consuming memory: `docker exec tailpaste ps aux`

## Health Check Monitoring

Container now has health checks:
```bash
# Check health status
docker inspect tailpaste --format='{{.State.Health.Status}}'

# View health check history
docker inspect tailpaste --format='{{json .State.Health.Log}}' | python3 -m json.tool
```

## Logs Directory

When container is running, logs are saved to:
- `./logs/app-*.log` (on host, via mounted volume)
- `/var/log/tailpaste/app-*.log` (inside container)

Copy logs for analysis:
```bash
docker cp tailpaste:/var/log/tailpaste ./crash-logs-$(date +%s)/
```

## Common Issues & Solutions

### **Database Lock Error**
```
sqlite3.OperationalError: database is locked
```
- Multiple processes writing to DB
- Check: `docker exec tailpaste lsof | grep pastes.db`
- Fix: Stop container, check storage/ directory isn't corrupted

### **Permission Denied on /data**
```
PermissionError: [Errno 13] Permission denied: '/data'
```
- Volume mount has wrong permissions from host
- Check: `ls -la storage/` (should be writable)
- Fix: `chmod 777 storage/` and rebuild

### **Port Already in Use**
```
OSError: [Errno 98] Address already in use
```
- Port 8080 is taken by another service
- Check: `lsof -i :8080` or `netstat -tulpn | grep 8080`
- Fix: Change port in docker-compose.yml

### **Tailscale Auth Key Invalid**
```
tailscaled: cannot authenticate: invalid auth key
```
- Fix: Check TAILSCALE_AUTHKEY environment variable
- Regenerate key if expired

## Using Logs Directory for Post-Mortem Analysis

The new logging system saves separate log files for each crash:

```bash
# View all crash logs
ls -la ./logs/

# Search for error pattern across all crashes
grep -r "ERROR" ./logs/

# Check if crashes happen at specific times
grep "CRASH DETECTED" ./logs/app-*.log

# Get timeline of all crashes
for f in logs/app-*.log; do 
  echo "=== $f ===" 
  head -1 "$f"
done
```

## Advanced: Manual Inspection

```bash
# Keep container running even if app crashes (for inspection)
docker run -it --entrypoint /bin/sh -v tailscale-state:/var/lib/tailscale tailpaste-app:production

# Inside container, test the app manually
python /app/main.py

# Check dependencies
python -c "import flask; import requests; print('OK')"
```

## Getting Help with Logs

When reporting issues, provide:
1. Output from `./scripts/diagnose-container.sh`
2. Full app logs: `docker logs --tail 200 tailpaste`
3. Last few crash logs: `docker exec tailpaste ls -la /var/log/tailpaste/ | tail -5`
4. Host system info: `uname -a && free -h && docker version`
