# Dockerfile for Hebrew University Course Catalog (HUJI Shnaton)
FROM python:3.11-slim

# Prevent python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PORT=8080 \
    HOST=0.0.0.0

WORKDIR /app

# Copy all repository files into container
COPY . /app

# Cloud Run / Render / Heroku listen port
EXPOSE 8080

# Run the pure-python web server
CMD ["python", "web_app.py"]
