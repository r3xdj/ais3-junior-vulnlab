FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends redis-server \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir celery redis

WORKDIR /app

COPY tasks.py /app/tasks.py
COPY decode_task.py /app/decode_task.py

COPY run.sh /app/run.sh
RUN chmod +x /app/run.sh

CMD ["/app/run.sh"]