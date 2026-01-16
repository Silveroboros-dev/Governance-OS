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
COPY alembic.ini /app/

# Set Python path to include app directory
ENV PYTHONPATH=/app

# Cloud Run sets PORT environment variable
ENV PORT=8080
EXPOSE 8080

# Production command (no reload)
CMD exec uvicorn core.main:app --host 0.0.0.0 --port $PORT
