FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install security scanning tools
RUN pip install --no-cache-dir \
    bandit \
    safety \
    semgrep \
    requests \
    numpy

# Install Gitleaks
RUN wget https://github.com/gitleaks/gitleaks/releases/download/v8.18.0/gitleaks_8.18.0_linux_x64.tar.gz \
    && tar -xzf gitleaks_8.18.0_linux_x64.tar.gz \
    && mv gitleaks /usr/local/bin/ \
    && rm gitleaks_8.18.0_linux_x64.tar.gz

# Install Trivy
RUN wget https://github.com/aquasecurity/trivy/releases/download/v0.48.0/trivy_0.48.0_Linux-64bit.tar.gz \
    && tar -xzf trivy_0.48.0_Linux-64bit.tar.gz \
    && mv trivy /usr/local/bin/ \
    && rm trivy_0.48.0_Linux-64bit.tar.gz

# Create working directories
RUN mkdir -p /code_to_audit /reports /app

# Copy audit script
COPY audit.py /app/audit.py

WORKDIR /app

# Set environment variables
ENV CODE_PATH=/code_to_audit
ENV REPORT_PATH=/reports
ENV PYTHONUNBUFFERED=1

# Run the auditor
CMD ["python", "-u", "audit.py"]
