#!/bin/bash
# Ensure required tools are installed
# This script ensures iptables and ping are available

set -euo pipefail

if ! command -v iptables > /dev/null; then
  sudo apt-get update && sudo apt-get install -y iptables
fi
