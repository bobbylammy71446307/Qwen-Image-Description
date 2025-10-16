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
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p /app/output /app/images /app/models

# Set environment variables (can be overridden)
ENV PYTHONUNBUFFERED=1

# Default command (can be overridden in docker-compose or at runtime)
CMD ["python", "/app/scripts/image_description.py"]
