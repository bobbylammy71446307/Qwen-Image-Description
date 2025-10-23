# Font Installation Guide

## Problem
The script shows warnings:
```
[WARNING] No Chinese font found for header, using default
[WARNING] No Chinese font found for body, using default
```

This happens when Chinese fonts are not installed on the system, causing Chinese text to display incorrectly in annotated images.

## Solutions

### Option 1: Install Fonts on Ubuntu/Debian Server

On the remote machine, run:

```bash
sudo bash install_fonts.sh
```

Or manually install:

```bash
sudo apt-get update
sudo apt-get install -y fonts-noto-cjk fonts-wqy-zenhei
sudo fc-cache -f -v
```

### Option 2: Install Fonts in Docker Container

If running in Docker, add this to your Dockerfile:

```dockerfile
# Install Chinese fonts
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        fonts-wqy-zenhei \
        fonts-noto-cjk && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    fc-cache -f -v
```

Or use the provided script in your Dockerfile:

```dockerfile
COPY install_fonts_docker.sh /tmp/
RUN bash /tmp/install_fonts_docker.sh
```

### Option 3: Install Fonts in Running Docker Container

If you have a running container:

```bash
# Copy script to container
docker cp install_fonts_docker.sh <container_name>:/tmp/

# Execute in container
docker exec -it <container_name> bash /tmp/install_fonts_docker.sh
```

Or manually:

```bash
docker exec -it <container_name> bash -c "apt-get update && apt-get install -y fonts-noto-cjk fonts-wqy-zenhei"
```

### Option 4: Quick Test (No Installation)

The script will still work with default fonts, but Chinese characters may appear as boxes or not render correctly. The functionality is not affected, only the visual appearance.

## Verification

After installation, verify fonts are available:

```bash
# List Chinese fonts
fc-list :lang=zh

# Check for Noto CJK
fc-list | grep -i noto | grep -i cjk

# Check for WenQuanYi
fc-list | grep -i wenquanyi
```

## Recommended Fonts

**Best (Most Complete):**
- `fonts-noto-cjk` - Noto Sans CJK (supports Traditional Chinese)
- `fonts-noto-cjk-extra` - Extended character set

**Good (Lighter):**
- `fonts-wqy-zenhei` - WenQuanYi Zen Hei (Simplified & Traditional)
- `fonts-wqy-microhei` - WenQuanYi Micro Hei (Smaller)

**Traditional Chinese Specific:**
- `fonts-arphic-uming` - AR PL UMing (明體)
- `fonts-arphic-ukai` - AR PL UKai (楷體)

## File Sizes

- `fonts-noto-cjk`: ~70 MB
- `fonts-wqy-zenhei`: ~8 MB
- `fonts-wqy-microhei`: ~2 MB

For Docker containers, `fonts-wqy-zenhei` is recommended for a good balance of size and quality.

## Troubleshooting

**Font still not found after installation:**
```bash
# Refresh font cache
sudo fc-cache -f -v

# Restart your Python script
```

**Check script output:**
The script will show which font it loaded:
```
[INFO] Loaded header font: /usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc
[INFO] Loaded body font: /usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc
```

**Permission issues:**
Make sure the font directories are readable:
```bash
sudo chmod -R 755 /usr/share/fonts/
```
