FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install git since the agent needs it for cloning/diffing if applicable
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
 && rm -rf /var/lib/apt/lists/*

# Copy dependencies first for caching layer
COPY pyproject.toml .

# Install dependencies
RUN pip install --no-cache-dir .

# Copy the rest of the application
COPY . .

# Expose the dashboard port
EXPOSE 8080

# Run the web dashboard
CMD ["python", "dashboard/server.py", "--port", "8080"]
