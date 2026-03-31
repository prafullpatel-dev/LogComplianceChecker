FROM python:3.11-slim

WORKDIR /app

# Copy only dependency files first (to leverage Docker layer caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy your Python files
COPY . .

# Run the producer
CMD ["python", "main.py"]
