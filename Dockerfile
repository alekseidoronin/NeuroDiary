FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ app/
# Copy admin app build (expects admin-app/dist to exist locally)
# Using mkdir to ensure structure matches
COPY admin-app/dist/ admin-app/dist/

# Set Python path
ENV PYTHONPATH=/app

# Default command
CMD ["python", "-m", "app.main", "polling"]
