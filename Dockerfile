FROM python:3.11-slim

# Set environment variables to prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install google-cloud-secret-manager for GCP Secret Management
RUN pip install --no-cache-dir google-cloud-secret-manager

# Copy the rest of the application code
COPY . .

# The command is overridden by docker-compose.yml
CMD ["python", "core/alpha_scanner.py"]
