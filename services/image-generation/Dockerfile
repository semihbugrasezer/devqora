FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for image processing
RUN apt-get update && apt-get install -y \
    gcc \
    libjpeg-dev \
    libpng-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY *.py /app/

# Create output directories
RUN mkdir -p /app/generated_images /app/logs

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python", "/app/nano_banana_client.py"]
