#!/bin/bash
# Lightweight font installation for Docker containers
# This installs minimal Chinese fonts to keep image size small

set -e

echo "Installing minimal Chinese fonts for Docker..."

# Update package list
apt-get update -qq

# Install only essential Chinese fonts (smaller package)
apt-get install -y --no-install-recommends \
    fonts-wqy-zenhei \
    fonts-noto-cjk

# Clean up to reduce image size
apt-get clean
rm -rf /var/lib/apt/lists/*

# Refresh font cache
fc-cache -f -v > /dev/null 2>&1 || true

echo "✓ Chinese fonts installed successfully"
