# Use Python 3.13 slim image as base
FROM python:3.13-slim

# Accept build argument from CapRover (eliminates warning)
ARG CAPROVER_GIT_COMMIT_SHA=unknown

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run.py \
    FLASK_ENV=production \
    GIT_COMMIT_SHA=${CAPROVER_GIT_COMMIT_SHA}

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p instance logs

# Copy and set up entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Expose port (CapRover will map this)
EXPOSE 80

# Use entrypoint script to run migrations before starting app
ENTRYPOINT ["docker-entrypoint.sh"]