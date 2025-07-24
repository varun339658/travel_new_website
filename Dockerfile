# Use official Python base image matching your runtime
FROM python:3.11.4-slim

# Set working directory
WORKDIR /app

# Copy files into the container
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port Flask or Gunicorn will use
EXPOSE 5000

# Set environment variables (optional)
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Run using gunicorn (production ready) or fallback to flask for development
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
