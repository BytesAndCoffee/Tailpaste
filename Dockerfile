# Dockerfile
# Multi-stage Dockerfile for tailpaste with integrated Tailscale

# Base stage with common setup
FROM tailscale/tailscale:latest AS base

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python and essential dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    sudo \
    shadow \
    curl && \
    pip3 install --break-system-packages -r requirements.txt && \
    ln -sf python3 /usr/bin/python

# Create inspector user
RUN adduser -D -s /bin/sh inspector && \
    echo "inspector ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers && \
    mkdir -p /home/inspector/.ssh && \
    chown -R inspector:inspector /home/inspector

# Copy application code
COPY main.py .
COPY src/ ./src/
COPY scripts/ /home/inspector/scripts/
COPY config.toml.example ./config.example.toml
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Expose HTTP server port
EXPOSE 8080

# Set default environment variables
ENV STORAGE_PATH=/data \
    LISTEN_PORT=8080 \
    TS_STATE_DIR=/var/lib/tailscale \
    TS_SOCKET=/var/run/tailscale/tailscaled.sock

# Run the application via entrypoint script
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["python", "main.py"]

# Stage 1: Runtime image (minimal) - this is the default
FROM base AS runtime

# Runtime uses base as-is (minimal footprint)

# Stage 2: Debug image (includes development and debugging tools)
FROM base AS debug

# Install build dependencies and debugging tools on top of base
RUN apk add --no-cache \
    python3-dev \
    gcc \
    musl-dev \
    linux-headers \
    htop \
    vim \
    nano \
    procps \
    net-tools \
    bind-tools \
    tcpdump \
    strace
