FROM python:3.11-slim
 
# System dependencies needed for psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*
 
WORKDIR /app
 
# Install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
 
# Copy the rest of the project
COPY . .
 
# Collect static files
RUN python manage.py collectstatic --noinput
 
EXPOSE 8000
 
# Migrate then start uvicorn (ASGI required for Django Channels / WebSockets)
CMD ["sh", "-c", "python manage.py migrate && uvicorn Hopeir.asgi:application --host 0.0.0.0 --port 8000 --workers 1"]
 