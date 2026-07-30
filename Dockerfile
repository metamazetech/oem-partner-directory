# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Install system dependencies (including Tesseract OCR for card scanning and other utilities)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies and Gunicorn for production WSGI server
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# Copy the rest of the application files
COPY . .

# Ensure data and upload directories exist with proper write permissions
RUN mkdir -p uploads data && chmod -R 777 uploads data

# Set environment variables
ENV PORT=5000
ENV DATABASE_PATH=/app/data/oem_tracker.db

# Expose port 5000 for Gunicorn
EXPOSE 5000

# Start Gunicorn server with 4 worker processes and 2 threads
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", "app:app"]
