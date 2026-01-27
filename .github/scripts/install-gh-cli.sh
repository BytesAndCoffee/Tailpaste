#!/bin/bash
set -e

echo "📦 Installing GitHub CLI from official repository..."

# Add GitHub CLI official apt repository
echo "Adding GitHub CLI official repository..."
sudo mkdir -p -m 755 /etc/apt/keyrings

# Download and install the GitHub CLI GPG key
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/etc/apt/keyrings/githubcli-archive-keyring.gpg
sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg

# Add the repository to apt sources
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null

# Update and install
echo "Installing GitHub CLI..."
sudo apt-get update
sudo apt-get install -y gh

# Verify installation
if command -v gh &> /dev/null; then
    echo "✅ GitHub CLI installed successfully"
    gh --version
else
    echo "❌ GitHub CLI installation failed"
    exit 1
fi
