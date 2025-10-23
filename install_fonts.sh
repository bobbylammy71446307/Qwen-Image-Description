#!/bin/bash
# Script to install Chinese fonts for image annotation
# Run with: sudo bash install_fonts.sh

set -e

echo "================================================"
echo "Installing Chinese Fonts for Image Annotation"
echo "================================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

# Update package list
echo ""
echo "[Step 1/3] Updating package list..."
apt-get update

# Install Chinese font packages
echo ""
echo "[Step 2/3] Installing Chinese font packages..."
echo "This may take a few minutes..."

# Install Noto CJK fonts (best support for Traditional Chinese)
apt-get install -y fonts-noto-cjk fonts-noto-cjk-extra

# Install WenQuanYi fonts (backup option)
apt-get install -y fonts-wqy-zenhei fonts-wqy-microhei

# Optional: Install additional fonts for better coverage
apt-get install -y fonts-arphic-uming fonts-arphic-ukai

# Refresh font cache
echo ""
echo "[Step 3/3] Refreshing font cache..."
fc-cache -f -v

# Verify installation
echo ""
echo "================================================"
echo "Verifying font installation..."
echo "================================================"

if fc-list | grep -qi "noto.*cjk"; then
    echo "✓ Noto CJK fonts installed successfully"
else
    echo "✗ Noto CJK fonts may not be installed correctly"
fi

if fc-list | grep -qi "wenquanyi"; then
    echo "✓ WenQuanYi fonts installed successfully"
else
    echo "✗ WenQuanYi fonts may not be installed correctly"
fi

if fc-list | grep -qi "ar pl"; then
    echo "✓ AR PL fonts installed successfully"
else
    echo "✗ AR PL fonts may not be installed correctly"
fi

echo ""
echo "================================================"
echo "Installation complete!"
echo "================================================"
echo ""
echo "Available Chinese fonts:"
fc-list :lang=zh | head -n 10
echo ""
echo "Your script should now be able to use Chinese fonts."
