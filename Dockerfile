FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgtk-3-0 \
    libgl1 \
    fonts-dejavu-core \
    fontconfig \
    cron \
    chromium \
    chromium-driver \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create necessary directories and cron log
RUN mkdir -p /app/output /app/images /app/models /app/logs && \
    touch /app/logs/cron.log && \
    chmod 0666 /app/logs/cron.log

# Set environment variables (can be overridden)
ENV PYTHONUNBUFFERED=1

# Setup cron job and permissions
RUN if [ -f /app/crontab ]; then \
        cp /app/crontab /etc/cron.d/image-description-cron && \
        chmod 0644 /etc/cron.d/image-description-cron && \
        crontab /etc/cron.d/image-description-cron; \
    fi

# Default command: start cron and tail the log file
CMD ["/bin/sh", "-c", "touch /app/logs/cron.log && cron && tail -f /app/logs/cron.log"]
