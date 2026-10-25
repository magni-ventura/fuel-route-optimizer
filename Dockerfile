
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system packages needed by Python dependencies.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       gcc \
       libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for better build caching.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the Django project.
COPY . .

# Support file-based application logging if configured in Django.
RUN mkdir -p /app/logs

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
