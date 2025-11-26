# flux-notebooks/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install basic utilities
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies from requirements.txt
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy the source code into the container
COPY . .

# Default command to run the Dash app
CMD ["python", "app.py"]
