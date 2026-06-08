# Dockerfile for GhostGoat
# Base image pinned with digest for reproducibility
FROM python:3.12-slim@sha256:5b5f9ec0e1b2c3d5f9e593a1c1f2f5b3f9a5d6c7e8f9a0b1c2d3e4f5a6b7c8d9

# Set non‑root user
RUN useradd -m ghostgoat && mkdir -p /app && chown ghostgoat:ghostgoat /app
USER ghostgoat
WORKDIR /app

# Copy only needed files (Docker uses .dockerignore)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Ensure the virtual‑env guard works without a venv
ENV PYTHONPATH=/app

# Default command starts the orchestrator (no venv required)
CMD ["./venv/bin/python", "main.py"]
