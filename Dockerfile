FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .

# Railway sets PORT environment variable
ENV PORT=8000
ENV HOST=0.0.0.0

EXPOSE 8000

# Health check endpoint (the server returns 404 on root but that's fine)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT}/sse || exit 1

# Run the HTTP/SSE server
CMD ["python", "-m", "ticktick_sdk.server_http"]
