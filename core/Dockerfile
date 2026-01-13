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

# Expose port
EXPOSE 8000

# Default command (will be overridden by docker-compose)
CMD ["uvicorn", "core.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
