# tailpaste

[![CI](https://github.com/BytesAndCoffee/Tailpaste/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/BytesAndCoffee/Tailpaste/actions/workflows/ci.yml) [![Deploy](https://github.com/BytesAndCoffee/Tailpaste/actions/workflows/deploy.yml/badge.svg?branch=main)](https://github.com/BytesAndCoffee/Tailpaste/actions/workflows/deploy.yml) [![Integration Tests](https://github.com/BytesAndCoffee/Tailpaste/actions/workflows/integration-test.yml/badge.svg?branch=main)](https://github.com/BytesAndCoffee/Tailpaste/actions/workflows/integration-test.yml) [![Security & Dependency Scanning](https://github.com/BytesAndCoffee/Tailpaste/actions/workflows/security.yml/badge.svg?branch=main)](https://github.com/BytesAndCoffee/Tailpaste/actions/workflows/security.yml) [![Health Check](https://github.com/BytesAndCoffee/Tailpaste/actions/workflows/health-check.yml/badge.svg?branch=main)](https://github.com/BytesAndCoffee/Tailpaste/actions/workflows/health-check.yml) [![Release](https://github.com/BytesAndCoffee/Tailpaste/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/BytesAndCoffee/Tailpaste/actions/workflows/release.yml)

A minimalist paste-sharing service inspired by ix.io that leverages Tailscale for authentication and network access control. Upload pastes from your tailnet, then expose read-only access through the public endpoint of your choice.

## Features

- **Tailnet-only uploads**: Only authenticated hosts on your tailnet can create pastes
- **Public viewing**: Anyone can view pastes via a public HTTP(S) endpoint you control
- **Custom domain support**: Serve pastes via your own domain (e.g., paste.bytes.coffee)
- **Simple CLI**: Upload pastes using curl or similar tools
- **SQLite storage**: Lightweight, file-based persistence
- **Property-based tested**: Comprehensive test coverage with Hypothesis

## Documentation

- **[CI/CD Pipeline](docs/CI_CD.md)** - Complete CI/CD documentation, workflows, monitoring, and best practices
- **[Service Inspector Guide](docs/INSPECTOR_GUIDE.md)** - SSH access and debugging with the inspector user
- **[Contributing Guidelines](CONTRIBUTING.md)** - How to contribute to the project
- **[Scripts Documentation](scripts/README.md)** - Monitoring and development scripts

## Prerequisites

- Python 3.8 or higher
- Tailscale installed and running on the host machine
- A Tailscale account with a configured tailnet

## Docker Deployment

### Quick Start

1. **Generate Tailscale auth key** at [Tailscale Admin Console](https://login.tailscale.com/admin/settings/keys)
   - Check "Ephemeral" and optionally "Reusable"
   - Copy the key (starts with `tskey-auth-`)

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your auth key
   ```

3. **Start the service**
   ```bash
   docker compose up -d
   ```

4. **Verify**
   ```bash
   docker compose ps                    # Check status
   docker compose logs -f               # View logs
   docker compose exec tailpaste tailscale status # Check tailscale status in container
   tailscale ssh inspector@tailpaste    # SSH for debugging
   ```

Service accessible at `http://<hostname>.your-tailnet.ts.net:8080/`

### Updating

```bash
git pull
docker compose up --build -d
```

### Stopping

```bash
docker compose down      # Stop container
docker compose down -v   # Stop and remove volumes
```

## Installation

### Local Installation

```bash
# Clone and setup
git clone https://github.com/BytesAndCoffee/Tailpaste.git
cd tailpaste
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure
cp config.example.toml config.toml
# Edit config.toml with your settings

# Run
python main.py
```

Service starts on port 8080 (or configured port).

## Configuration

Configuration via environment variables or `config.toml` (environment variables take precedence).

### Options

| Option | Environment Variable | Default | Description |
|--------|---------------------|---------|-------------|
| Custom Domain | `CUSTOM_DOMAIN` | None | Custom domain for paste URLs |
| Storage Path | `STORAGE_PATH` | `./storage/pastes.db` | SQLite database path |
| Listen Port | `LISTEN_PORT` | `8080` | HTTP server port |
| Tailscale Socket | `TAILSCALE_SOCKET` | Auto-detected | LocalAPI socket path |

### Example config.toml

```toml
custom_domain = "paste.bytes.coffee"
storage_path = "./storage/pastes.db"
listen_port = 8080
```

### Example environment variables

```bash
export CUSTOM_DOMAIN="paste.bytes.coffee"
export STORAGE_PATH="./storage/pastes.db"
export LISTEN_PORT=8080
```

## Public Exposure Setup

Tailpaste accepts uploads only from your tailnet, but you can expose read-only access publicly using a reverse proxy.

**Example**: Configure nginx to forward public `GET /<paste-id>` requests to the tailnet service while keeping `POST /` restricted to your tailnet.

## Custom Domain Configuration

To serve pastes via a custom domain (e.g., `paste.bytes.coffee`):

1. **Configure DNS**: Add CNAME record pointing to your public hostname
2. **Update configuration**: Set `custom_domain = "paste.bytes.coffee"` in config or `CUSTOM_DOMAIN` env variable
3. **Enable HTTPS**: Provision TLS certificates via your reverse proxy
4. **Restart service**: Paste URLs will now use your custom domain

## Usage

### Upload a Paste (from Tailnet)

```bash
# From stdin
echo "Hello, world!" | curl -d @- http://tailpaste:8080

# From file
curl -d @script.py http://tailpaste:8080

# Heredoc
curl -d @- http://tailpaste:8080 <<EOF
Multi-line paste
with several lines
EOF
```

Returns: `https://paste.bytes.coffee/abc12345`

### View a Paste (Public)

```bash
# Terminal
curl https://paste.bytes.coffee/abc12345

# Browser
# https://paste.bytes.coffee/abc12345
```

Browser viewing renders HTML with monospace font, preserved whitespace, and proper character escaping.

### Optional Shell Alias

```bash
# Add to .bashrc or .zshrc
alias paste='curl -d @- http://tailpaste:8080'

# Usage
echo "Quick paste" | paste
cat file.txt | paste
```

## Development

### Install Development Dependencies

```bash
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest                        # Run all tests
pytest -v                     # Verbose output
pytest tests/test_storage.py  # Specific test file
pytest -k "property"          # Property-based tests only
pytest --cov=src tests/       # With coverage
```

The service includes both unit tests and property-based tests with [Hypothesis](https://hypothesis.readthedocs.io/) for intelligent test case generation (100+ iterations each).

For CI/CD setup, monitoring, and deployment procedures, see [docs/CI_CD.md](docs/CI_CD.md).

## Architecture

```
┌─────────────────┐
│  Tailnet User   │
└────────┬────────┘
         │ POST /
         ▼
┌─────────────────┐      ┌──────────────────┐
│  Flask Server   │─────▶│  Authenticator   │
└────────┬────────┘      └──────────────────┘
         │                        │
         │                        ▼
         │               ┌──────────────────┐
         │               │ Tailscale        │
         │               │ LocalAPI         │
         │               └──────────────────┘
         ▼
┌─────────────────┐      ┌──────────────────┐
│  PasteHandler   │─────▶│  IDGenerator     │
└────────┬────────┘      └──────────────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│    Storage      │─────▶│  SQLite DB       │
└─────────────────┘      └──────────────────┘

┌─────────────────┐
│ Public Viewer   │
└────────┬────────┘
         │ GET /<id>
         ▼
┌─────────────────┐      ┌──────────────────┐
│  Flask Server   │─────▶│    Renderer      │
└────────┬────────┘      └──────────────────┘
         │
         ▼
┌─────────────────┐
│    Storage      │
└─────────────────┘
```

## Security

- **Upload authentication**: Only tailnet hosts can create pastes (verified via Tailscale LocalAPI)
- **Public viewing**: Pastes are publicly accessible once created (by design)
- **HTML escaping**: All paste content is properly escaped when rendered as HTML
- **No user accounts**: Authentication is handled entirely by Tailscale
- **TLS encryption**: All traffic encrypted via your chosen HTTPS termination

## Troubleshooting

### Service won't start

```bash
# Create storage directory
mkdir -p storage

# Verify Tailscale is running
tailscale status

# Check socket path (Linux/macOS)
ls -la /var/run/tailscale/tailscaled.sock
```

### Uploads fail with 403 Forbidden

- Verify you're uploading from a device on your tailnet
- Check `tailscale status` to confirm connection
- Verify the service can reach Tailscale LocalAPI

### Custom domain not resolving

- Verify DNS CNAME record: `dig paste.bytes.coffee` or `nslookup paste.bytes.coffee`
- Allow time for DNS propagation (up to 48 hours)

For detailed troubleshooting, deployment issues, and monitoring, see [docs/CI_CD.md](docs/CI_CD.md).

## Service Inspection via SSH

The Docker container includes an `inspector` user for debugging via Tailscale SSH:

```bash
tailscale ssh inspector@tailpaste
```

The inspector user has full sudo access and pre-installed debugging tools (htop, curl, vim, tcpdump, strace, etc.).

**Common commands**:
```bash
ps aux | grep python          # Check service status
curl http://tailpaste:8080/   # Test endpoints
sudo netstat -tlnp            # Monitor connections
htop                          # View processes
```

For complete details, see the [Service Inspector Guide](docs/INSPECTOR_GUIDE.md).

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Here's how to get started:

1. Fork and clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Install Git hooks: `./scripts/setup-hooks.sh`
4. Create a feature branch: `git checkout -b feature/amazing-feature`
5. Make your changes and write tests
6. Ensure tests pass: `pytest tests/ -v`
7. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines, including:
- Development setup and workflow
- Code style and testing guidelines
- Pull request process
- Areas for contribution

For CI/CD and monitoring setup, see [docs/CI_CD.md](docs/CI_CD.md)

## Acknowledgments

- Built with [Tailscale](https://tailscale.com/) for zero-trust networking
- Inspired by [ix.io](http://ix.io/) for simplicity
- Property-based testing with [Hypothesis](https://hypothesis.readthedocs.io/)
