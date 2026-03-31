FROM python:3.11-slim

WORKDIR /app

# Copy only dependency files first (to leverage Docker layer caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of your code
COPY . .

# Run the app
CMD ["python", "-u", "main.py"]