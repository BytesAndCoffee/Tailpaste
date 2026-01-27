# Container Crash Diagnostics - Summary

I've enhanced your setup with comprehensive crash detection and logging. Here's what was done:

## ✅ Changes Made

### 1. **Enhanced Entrypoint Script** (`docker-entrypoint.sh`)
- Added detailed crash logging with exit codes and timestamps
- Captures full application logs to `/var/log/tailpaste/app-*.log`
- Interprets exit codes (137=OOMKill, 143=SIGTERM, etc.)
- Monitors system resources when crashes occur
- Shows last 20 lines from app log on each crash
- Detects crash loops (5+ crashes in 5 minutes) and stops restarting

### 2. **Docker Compose Improvements** (`docker-compose.yml`)
- Added health checks every 30 seconds
- Set resource limits (2 CPUs, 512MB max memory)
- Added volume mount for logs: `./logs/` → `/var/log/tailpaste/`
- Easy identification of OOMKilled containers

### 3. **Diagnostic Tools**

#### **`scripts/diagnose-container.sh`** - Full diagnostic report
```bash
./scripts/diagnose-container.sh
```
Shows:
- Container status and exit code
- OOMKill status
- Recent logs (last 50 lines)
- Current resource usage
- Mounted volumes
- Network configuration
- Exit code reference guide

#### **`scripts/monitor-container.sh`** - Real-time monitoring
```bash
./scripts/monitor-container.sh
```
Continuously watches for:
- Container starts/stops
- Exit codes
- OOMKill events
- App process restarts
- Logs all events to `container-monitor.log`

### 4. **Documentation** (`docs/CONTAINER_DEBUGGING.md`)
Complete guide with:
- Quick diagnostic commands
- Exit code meanings
- Common crash causes
- Solutions for each issue
- Advanced debugging techniques

## 🚀 How to Use

### **When Your Container Crashes:**

1. **Get a full diagnostic snapshot:**
   ```bash
   ./scripts/diagnose-container.sh
   ```

2. **Watch logs live:**
   ```bash
   docker logs -f tailpaste
   ```

3. **Check what killed it:**
   ```bash
   # Exit code
   docker inspect tailpaste --format='{{.State.ExitCode}}'
   
   # Was it out of memory?
   docker inspect tailpaste --format='{{.State.OOMKilled}}'
   ```

4. **View crash logs:**
   ```bash
   # From host (mounted volume)
   ls -la logs/
   tail -50 logs/app-*.log
   
   # From inside container
   docker exec tailpaste tail -100 /var/log/tailpaste/app-*.log
   ```

5. **Monitor continuously:**
   ```bash
   ./scripts/monitor-container.sh
   ```

## 📊 Key Information Collected

When container crashes, entrypoint logs:
- ✅ Exact timestamp
- ✅ Process PID that died
- ✅ Exit code (with interpretation)
- ✅ System memory/disk status
- ✅ Last 20 lines of app log
- ✅ Number of crashes in current window

## 🔍 What Each Exit Code Means

| Code | Meaning | Likely Cause |
|------|---------|--------------|
| 0 | Clean exit | Config error, missing dependency |
| 1 | Generic error | Python exception, missing file |
| 127 | Command not found | Binary missing, path issue |
| 137 | SIGKILL | **OUT OF MEMORY** (OOMKilled) or external kill |
| 139 | SIGSEGV | Segmentation fault, memory corruption |
| 143 | SIGTERM | Graceful termination (normal Docker stop) |

## 🛡️ Resource Limits

Currently set to:
- **Max Memory**: 512MB
- **Max CPUs**: 2.0
- **Guaranteed Memory**: 256MB
- **Guaranteed CPUs**: 0.5

If getting OOMKilled, increase in docker-compose.yml:
```yaml
deploy:
  resources:
    limits:
      memory: 1G  # Increase this
```

## 📁 Log Locations

**Host Machine:**
- `./logs/` - mounted from container's `/var/log/tailpaste/`
- `./logs/app-TIMESTAMP.log` - individual app crash logs

**Inside Container:**
- `/var/log/tailpaste/app-*.log` - crash logs
- Docker logs: `docker logs tailpaste`

## 💡 Next Steps

1. **Rebuild and restart:**
   ```bash
   docker-compose build
   docker-compose up -d
   ```

2. **Run diagnostic immediately:**
   ```bash
   ./scripts/diagnose-container.sh
   ```

3. **Start monitoring:**
   ```bash
   ./scripts/monitor-container.sh &
   ```

4. **If it crashes, check:**
   - `logs/app-*.log` (most recent)
   - `container-monitor.log` (timeline of events)
   - `docker inspect tailpaste --format='{{.State.OOMKilled}}'` (memory issue?)

## 🆘 Getting Help

If container still keeps crashing, provide:

1. Output from diagnostic script:
   ```bash
   ./scripts/diagnose-container.sh > diagnostics.txt 2>&1
   ```

2. Full logs (last 200 lines):
   ```bash
   docker logs --tail 200 tailpaste > container-logs.txt 2>&1
   ```

3. Crash logs:
   ```bash
   cp logs/* crash-logs/
   ```

4. System info:
   ```bash
   uname -a && docker version && free -h
   ```
