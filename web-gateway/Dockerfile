# web-gateway/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# pycurl 需要編譯,補上 libcurl 開發套件與編譯工具
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libcurl4-openssl-dev \
        libssl-dev \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ .

EXPOSE 5000
CMD ["python", "app.py"]