# Use the official Python image as a parent image
FROM python:3.11-slim

# Install curl for health checks
RUN apt-get update && apt-get install -y curl jq && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --timeout 100 -r requirements.txt

# Copy the rest of the application's code to the working directory
COPY . .

# The command to run the application will be specified in docker-compose.yml
# This CMD is a fallback for running the container without docker-compose
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
