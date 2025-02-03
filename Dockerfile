# Base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY ./src /app

# Expose the Flask port
EXPOSE 5000

# Default command
CMD ["gunicorn", "--bind", "0.0.0.0:8008", "app:app"]
