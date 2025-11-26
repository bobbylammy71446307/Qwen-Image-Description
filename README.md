### Chinese Font Installation

On the host machine, run:


```bash
sudo apt-get update
sudo apt-get install -y fonts-noto-cjk fonts-wqy-zenhei
sudo fc-cache -f -v
```

### Install Fonts in Docker Container

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

