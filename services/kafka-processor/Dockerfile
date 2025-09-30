FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY services/kafka-processor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/kafka-processor/ .

# Run the processor
CMD ["python", "processor.py"]