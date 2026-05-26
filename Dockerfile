# Dockerfile
# CHANGED: Standard Dockerfile configuration (TASK 9)
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Run the bot
CMD ["python", "main.py"]
