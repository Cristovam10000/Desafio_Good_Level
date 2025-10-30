FROM postgres:15

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-15-cron \
    && rm -rf /var/lib/apt/lists/*

COPY docker/postgresql.conf /etc/postgresql/postgresql.conf
