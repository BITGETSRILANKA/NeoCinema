# Use Python 3.11 as the base
FROM python:3.11-slim

# Create a folder for the bot
WORKDIR /app

# Install dependencies first (faster builds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all code into the folder
COPY . .

# Tell Koyeb how to start it
CMD ["python", "main.py"]
