# Use a slim Python base image for a smaller container size
FROM python:3.9-slim

# Set environment variables to run Python in unbuffered mode (good for Docker logging)
ENV PYTHONUNBUFFERED 1

# Set the working directory inside the container
WORKDIR /app

# 1. Install dependencies
# CORRECTED: Files are copied relative to the build context (which is ./lb)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Copy the application files
# CORRECTED: Files are copied relative to the build context (which is ./lb)
COPY load_balancer.py .

# Expose the port the load balancer runs on
EXPOSE 8080

# Command to run the load balancer application
CMD ["python", "load_balancer.py"]
