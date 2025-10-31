FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY tools/generate_data.py ./generate_data.py

RUN pip install --no-cache-dir \
    faker==25.8.0 \
    psycopg2-binary==2.9.9

CMD ["python", "generate_data.py"]
