# Use the official Python image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the backend requirements and install them
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy the frontend and backend folders into the container
COPY frontend/ ./frontend/
COPY backend/ ./backend/

# Set the working directory to backend so Uvicorn can find main.py
WORKDIR /app/backend

# Cloud Run injects the PORT environment variable (default 8080)
# We start uvicorn and bind it to 0.0.0.0 and the dynamic $PORT
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
