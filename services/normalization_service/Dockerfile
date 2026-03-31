FROM python:3.11-slim

WORKDIR /app

# Copy dependency file first for Docker layer caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run the normalization service
CMD ["python", "-u", "main.py"]
