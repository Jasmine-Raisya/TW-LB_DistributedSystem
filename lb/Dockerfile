# Use a slim Python base image for a smaller container size
FROM python:3.9-slim

# Set environment variables to run Python in unbuffered mode (good for Docker logging)
ENV PYTHONUNBUFFERED 1

# Set the working directory inside the container
WORKDIR /app

# 1. Install dependencies
# Build context is root (.), so we need to reference lb/ subdirectory
COPY lb/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Copy the application files
# Build context is root (.), so we need to reference lb/ subdirectory
COPY lb/load_balancer.py .

# 3. Copy ML model artifacts (from root directory)
# These will be copied from the root during build (see docker-compose.yml context mapping)
COPY artifacts/ ./artifacts/

# Expose the port the load balancer runs on
EXPOSE 8080

# Command to run the load balancer application
CMD ["python", "load_balancer.py"]
