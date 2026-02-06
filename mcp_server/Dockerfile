# MCP Server Dockerfile for Cloud Run deployment
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY core/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY core/ /app/core/
COPY mcp_server/ /app/mcp_server/
COPY packs/ /app/packs/

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# MCP server configuration for Cloud Run
ENV MCP_TRANSPORT=http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8080

# Cloud Run expects port 8080
EXPOSE 8080

# Run MCP server via __main__.py (avoids RuntimeWarning about module import order)
CMD ["python", "-m", "mcp_server"]
