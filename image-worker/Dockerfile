FROM python:3.10-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends imagemagick \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir flask

COPY app.py .

RUN mkdir -p /app/uploads /app/output

EXPOSE 5000

CMD ["python", "app.py"]
