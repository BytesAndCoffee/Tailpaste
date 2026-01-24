#!/bin/bash
# Check for elevated privileges

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "❌ This job requires elevated privileges."
  echo "Checking sudo access..."
  echo "Elevated user: $(sudo whoami)"
fi
echo "✓ Running with elevated privileges."
sudo which iptables
