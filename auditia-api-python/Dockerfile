# Using a lightweight Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PORT 8080

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Expose the port (Cloud Run uses PORT env var)
EXPOSE 8080

# Command to run the application
# Using uvicorn on the PORT specified by the environment
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
