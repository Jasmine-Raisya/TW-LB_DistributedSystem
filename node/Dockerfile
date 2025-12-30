# Use a slim Python base image
FROM python:3.9-slim

ENV PYTHONUNBUFFERED 1

# Set the working directory inside the container
WORKDIR /app

# 1. Install dependencies
# Assuming requirements.txt is in the node folder for the node build context (./node)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Copy the application files
# 2. Copy the application files
# Copy all python files (main.py, byzantine_faults.py, etc.)
COPY *.py .

# Expose the port the node service runs on
EXPOSE 8000

# Command to run the node application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
