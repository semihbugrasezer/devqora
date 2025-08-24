FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install pnpm
RUN npm install -g pnpm

# Install Wrangler CLI for Cloudflare Pages
RUN npm install -g wrangler

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY *.py ./

# Create sites directory
RUN mkdir -p /sites

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import redis; r=redis.Redis(host='redis'); r.ping()" || exit 1

CMD ["python", "content_scheduler.py"]