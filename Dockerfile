FROM python:3.11-slim

WORKDIR /app

# Copy all files needed for build
COPY pyproject.toml README.md ./
COPY src/ src/

# Install the package
RUN pip install --no-cache-dir .

# Railway sets PORT environment variable
ENV PORT=8000
ENV HOST=0.0.0.0

EXPOSE 8000

# Run the HTTP/SSE server
CMD ["python", "-m", "ticktick_sdk.server_http"]
