# Base lightweight Python image
FROM python:3.10-slim

# Create and set working directory
WORKDIR /app

# Copy project files into container
COPY . /app

# Install dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose the default Hugging Face port
EXPOSE 7860

# Run Flask app via Gunicorn for production stability
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:7860", "app:app"]
