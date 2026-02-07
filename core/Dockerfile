FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for Docker layer caching)
COPY core/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY core/ /app/core/
COPY db/ /app/db/
COPY packs/ /app/packs/
COPY coprocessor/ /app/coprocessor/
COPY alembic.ini /app/

# Copy and prepare entrypoint script
COPY core/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set Python path to include app directory
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Use entrypoint script (auto-seeds policies on first run)
ENTRYPOINT ["/app/entrypoint.sh"]
