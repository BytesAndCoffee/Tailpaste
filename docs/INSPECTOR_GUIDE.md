# Service Inspector Guide

## SSH Access via Tailscale SSH

The container includes an `inspector` user specifically for debugging and service inspection via Tailscale SSH.

### Connecting

```bash
# Connect via Tailscale SSH
tailscale ssh inspector@tailpaste

# Or if you've set a custom hostname
tailscale ssh inspector@<your-hostname>
```

### Available Tools

The inspector user has access to the following debugging tools:

- **htop** - Interactive process viewer
- **curl** - HTTP client for testing endpoints
- **vim/nano** - Text editors
- **tcpdump** - Network packet analyzer (requires sudo)
- **strace** - System call tracer
- **netstat** - Network statistics
- **dig/nslookup** - DNS lookup tools
- **ps/top** - Process monitoring
- **sudo** - Full root access for inspection

### Common Inspection Tasks

#### Check Service Status

```bash
# View running processes
ps aux | grep python

# Check application logs
sudo tail -f /app/logs/* 2>/dev/null || echo "No log files in /app/logs"

# View recent Docker logs (if accessible)
# Note: Docker logs are typically viewed from the host
```

#### Test Endpoints

```bash
# Test local endpoint
curl -v http://localhost:8080/

# Test health check (if available)
curl http://localhost:8080/health 2>/dev/null || echo "No health endpoint"

# Create a test paste
curl -X POST http://localhost:8080/paste \
  -H "Content-Type: application/json" \
  -d '{"content": "test paste", "language": "text"}'
```

#### Monitor Performance

```bash
# Interactive process viewer
htop

# Monitor in real-time
top

# Check memory usage
free -m

# Check disk usage
df -h

# Check data directory
du -sh /data/*
```

#### Network Inspection

```bash
# Check listening ports
sudo netstat -tlnp

# Check Tailscale status
tailscale status

# Check network connections
sudo netstat -tunap

# Capture traffic (requires sudo)
sudo tcpdump -i any -n port 8080
```

#### Database Inspection

```bash
# If using SQLite
ls -lh /data/*.db

# Check database size and permissions
stat /data/*.db 2>/dev/null || echo "No database files found"

# Access SQLite (if sqlite3 is available)
# apk add sqlite
# sqlite3 /data/tailpaste.db
```

#### Application Debugging

```bash
# Check Python processes
ps aux | grep python

# Follow application with strace
sudo strace -p $(pgrep -f "python.*main.py")

# Check application files
ls -la /app/

# View configuration
cat /config/config.toml 2>/dev/null || echo "No config file found"

# Check environment variables
sudo cat /proc/$(pgrep -f "python.*main.py")/environ | tr '\0' '\n'
```

#### System Information

```bash
# OS and kernel info
uname -a
cat /etc/os-release

# Check uptime
uptime

# View system logs
dmesg | tail -50
```

### Security Notes

- The `inspector` user has sudo access without password for debugging
- This is intended for development/debugging environments
- For production, consider:
  - Removing sudo access
  - Using Tailscale ACLs to restrict SSH access
  - Implementing audit logging
  - Using read-only access where possible

### Tailscale SSH Configuration

Tailscale SSH is configured with the `--ssh` flag in the container startup. You can modify SSH settings via:

1. **Tailscale ACLs** - Control who can SSH to the service
2. **SSH posture checks** - Require specific conditions before allowing access
3. **Session recording** - Enable SSH session recording in Tailscale admin

### Troubleshooting

#### Can't connect via SSH

```bash
# From your local machine, check Tailscale status
tailscale status

# Verify the service is online
tailscale ping tailpaste

# Check SSH is enabled on the service
tailscale ssh --check tailpaste
```

#### Permission denied

```bash
# Verify you're using the inspector user
whoami

# Check sudo access
sudo -l
```

#### Tools not available

```bash
# Install additional tools (Alpine Linux)
sudo apk add <package-name>

# Common packages
sudo apk add sqlite bind-tools iotop
```

## Additional Notes

- The inspector user is created during container build
- Password is randomly generated and not intended for direct use (Tailscale SSH handles authentication)
- All inspection should be non-destructive when possible
- Use `sudo` carefully as you have full root access
