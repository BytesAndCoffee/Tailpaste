#!/bin/bash
# Script to generate a Tailscale ephemeral auth key using the Tailscale API
# Requires: TAILSCALE_API_KEY environment variable or passed as first argument

set -e

# Get API key from environment or argument
API_KEY="${TAILSCALE_API_KEY:-$1}"

if [ -z "$API_KEY" ]; then
    echo "Error: Tailscale API key required"
    echo ""
    echo "Usage:"
    echo "  TAILSCALE_API_KEY=tskey-api-xxx ./generate-authkey.sh"
    echo "  OR"
    echo "  ./generate-authkey.sh tskey-api-xxx"
    echo ""
    echo "To create an API key:"
    echo "1. Visit: https://login.tailscale.com/admin/settings/keys"
    echo "2. Click 'Generate API access token'"
    echo "3. Give it a description (e.g., 'Paste Service Deployment')"
    echo "4. Copy the generated token (starts with 'tskey-api-')"
    exit 1
fi

# Get tailnet name (usually your email domain or GitHub username)
echo "Enter your tailnet name (e.g., example.com or github:username):"
read -r TAILNET

if [ -z "$TAILNET" ]; then
    echo "Error: Tailnet name required"
    exit 1
fi

echo "Generating ephemeral auth key for tailnet: $TAILNET"

# Call Tailscale API to create an ephemeral auth key
RESPONSE=$(curl -s -X POST \
    "https://api.tailscale.com/api/v2/tailnet/${TAILNET}/keys" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
        "capabilities": {
            "devices": {
                "create": {
                    "reusable": true,
                    "ephemeral": true,
                    "preauthorized": true,
                    "tags": ["tag:con"]
                }
            }
        },
        "expirySeconds": 3600,
        "description": "Paste Service"
    }')

# Extract the auth key from the response
AUTH_KEY=$(echo "$RESPONSE" | grep -o '"key":"[^"]*"' | cut -d'"' -f4)

if [ -z "$AUTH_KEY" ]; then
    echo "Error: Failed to generate auth key"
    echo "Response: $RESPONSE"
    exit 1
fi

echo ""
echo "✓ Auth key generated successfully!"
echo ""
echo "Add this to your .env file:"
echo ""
echo "TAILSCALE_AUTHKEY=$AUTH_KEY"
echo ""

# Optionally write to .env file
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    # Replace the placeholder with the actual key
    if command -v sed &> /dev/null; then
        sed -i.bak "s|TAILSCALE_AUTHKEY=.*|TAILSCALE_AUTHKEY=$AUTH_KEY|" .env
        rm .env.bak 2>/dev/null || true
        echo "✓ .env file created and configured"
    fi
else
    echo "Note: .env file already exists. Please update it manually."
fi

echo ""
echo "You can now start the service with:"
echo "  docker compose up -d"
