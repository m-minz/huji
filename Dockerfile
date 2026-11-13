# Dockerfile for Hebrew University Course Catalog (HUJI Shnaton)
FROM python:3.11-slim

# Prevent python from buffering stdout/stderr and enforce UTF-8
ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PORT=8080 \
    HOST=0.0.0.0

WORKDIR /app

# Copy all repository files into container
COPY . /app

# Cloud Run / Render / Heroku listen port
EXPOSE 8080

# Run the pure-python web server
CMD ["python", "web_app.py"]
