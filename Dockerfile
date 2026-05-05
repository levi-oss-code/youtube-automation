FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY youtube_uploader.py .

# Create directories
RUN mkdir -p videos uploaded metadata

# Copy token and secrets (provided via Render environment or secret files)
# token.pickle and client_secrets.json should be mounted as secret files in Render

CMD ["python", "main.py"]
