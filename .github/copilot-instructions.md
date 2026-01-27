# Tailpaste Copilot Instructions

## Architecture Overview

Tailpaste is a minimalist paste-sharing service with Tailscale authentication. The architecture separates upload authentication (tailnet-only) from read access (public).

**Core Components** (all in `src/`):
- `app.py` - Flask HTTP server with two routes: POST for uploads (authenticated), GET for retrieval (public)
- `authenticator.py` - Validates requests via Tailscale LocalAPI Unix socket (`/var/run/tailscale/tailscaled.sock`)
- `storage.py` - SQLite persistence with `Paste` dataclass (id, content, created_at, source_host, source_user)
- `paste_handler.py` - Orchestrates storage + ID generation + config
- `id_generator.py` - Generates URL-safe 8-char paste IDs
- `renderer.py` - Formats responses as plain text
- `config.py` - Env vars + TOML with priority: env > file > defaults

**Data Flow**: Request → Authenticator (whois via LocalAPI) → PasteHandler → Storage (SQLite)

## Critical Conventions

### Dependency Injection Pattern
All components follow explicit DI - see [`main.py`](main.py) initialization sequence:
```python
storage = Storage(database_path)
authenticator = Authenticator(tailscale_socket)
paste_handler = PasteHandler(storage, id_generator, config)
create_app(config, authenticator, paste_handler, renderer)
```
**Never instantiate components inside other components** - always pass via constructor.

### Error Handling
Each module defines custom exceptions (e.g., `StorageError`, `AuthenticationError`, `PasteHandlerError`). Always:
1. Catch specific exceptions at component boundaries
2. Log errors with context: `logger.error(f"Context: {details}")`
3. Convert to HTTP responses in `app.py` only

### Configuration Priority
[`src/config.py`](src/config.py#L41-L49) implements env > file > defaults. When adding config:
```python
# 1. Add to _ConfigValues TypedDict
# 2. Add env var parsing in from_env_and_file()
# 3. Add TOML parsing in _load_from_toml()
# 4. Set default in Config.__init__()
```

## Testing Strategy

Run tests: `pytest -v` (configured in [`pytest.ini`](pytest.ini))

**Test Structure**:
- Unit tests: Mock all dependencies, test single component
- Integration tests: Use real `Storage` with temp DB, mock only `Authenticator`
- Property tests: Mark with `@pytest.mark.property` for Hypothesis tests

**Mock Patterns** (from [`tests/test_app.py`](tests/test_app.py#L41-L51)):
```python
@pytest.fixture
def mock_authenticator():
    return Mock(spec=Authenticator)  # Always spec= to catch typos

mock_authenticator.verify_tailnet_source.return_value = sample_whois_info
```

## Docker & Deployment

### Container Architecture
[`Dockerfile`](Dockerfile) uses multi-stage builds:
- `base` - Tailscale + Python + app (default for production)
- `debug` - Adds dev tools (htop, vim, tcpdump, etc.)

Build: `docker compose build` or `docker compose build --target debug`

### Privileged Container Requirements
[`docker-compose.yml`](docker-compose.yml#L15-L22) requires:
- `privileged: true` for Tailscale kernel networking
- `cap_add: NET_ADMIN, SYS_MODULE` for TUN device
- `/dev/net/tun` device mount

**Never remove these** - Tailscale won't work without kernel networking.

### Inspector User Pattern
SSH debugging via `tailscale ssh inspector@tailpaste` (see [`Dockerfile`](Dockerfile#L20-L23)):
- Password-less sudo for debugging
- Scripts in `/home/inspector/scripts/`
- Used for live troubleshooting without exec

## Development Workflows

### Local Development
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp config.toml.example config.toml  # Edit with local settings
python main.py  # Starts on :8080
```

### Code Quality
Pre-commit hooks in `scripts/dev/`:
```bash
black src/ tests/        # Format (required)
flake8 src/ tests/       # Lint
mypy src/                # Type check
pytest -v                # All tests must pass
```

### CI/CD Pipeline
GitHub Actions in `.github/workflows/` (documented in [`docs/CI_CD.md`](docs/CI_CD.md)):
1. **CI** (push/PR) - Matrix test Python 3.10/3.11/3.12 → Docker build
2. **Integration Tests** (on CI success) - End-to-end container tests
3. **Security** (daily + push) - Dependency/container scanning
4. **Deploy** (on integration success) - Production deployment with rollback
5. **Health Check** (hourly) - Auto-recovery on failures

**Self-hosted runners** via ARC on Kubernetes - workflows may reference runner labels.

## Key Integration Points

### Tailscale LocalAPI
[`src/authenticator.py`](src/authenticator.py#L80-L115) uses `requests-unixsocket` to query whois:
```python
url = f"http+unix://{encoded_socket}/localapi/v0/whois?addr={remote_ip}"
```
Returns `WhoIsInfo` with node/user details. **LocalAPI must be accessible** - this is why socket path is configurable.

### Proxy Detection
[`src/app.py`](src/app.py#L66-L79) explicitly blocks proxy headers (`X-Forwarded-For`, etc.) to prevent auth bypass. Tailpaste requires **direct Tailscale connectivity** for uploads.

### Storage Schema
[`src/storage.py`](src/storage.py#L51-L58) SQLite table:
```sql
CREATE TABLE pastes (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    source_host TEXT NOT NULL,
    source_user TEXT NOT NULL
)
```
**No migrations** - schema is append-only by design.

## Health Monitoring

[`scripts/health/health_check.py`](scripts/health/health_check.py) provides comprehensive checks:
- HTTP endpoint availability
- Database integrity & size
- Tailscale connectivity
- Container status
- Response time metrics

Used by hourly GitHub Actions workflow. Returns JSON metrics and exit codes:
- 0 = healthy
- 1 = degraded (warnings)
- 2 = critical failure

## Common Pitfalls

1. **Don't bypass Authenticator** - All uploads MUST go through `verify_tailnet_source()`
2. **SQLite locking** - Use `timeout=30` in Storage connection to handle concurrent writes
3. **Container privileges** - Never run without NET_ADMIN or tests will fail silently
4. **Config precedence** - Env vars override TOML - document overrides in deployment docs
5. **Test isolation** - Always use `tempfile.TemporaryDirectory()` for test databases
