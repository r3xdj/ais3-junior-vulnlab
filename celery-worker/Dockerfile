FROM python:3.12-slim

# 安裝 cron(Stage 5 提權用)
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ .

# 建立一般使用者,Celery Worker 以此身份執行(Stage 4 拿到的 shell 是這個權限)
RUN useradd -m -u 1000 celeryuser

# Stage 4: 由 entrypoint 在啟動時從掛載的 /flags 複製 flag
RUN mkdir -p /home/celeryuser /root && \
    chown celeryuser:celeryuser /home/celeryuser

# Stage 5: 建立 world-writable 的 log 目錄,選手可以在這裡放惡意檔案
RUN mkdir -p /var/log/app /var/backups && \
    chmod 777 /var/log/app && \
    chmod 755 /var/backups

# Stage 5: 安裝以 root 身份執行的 crontab
# tar * 萬用字元注入漏洞:攻擊者在 /var/log/app 建立
#   --checkpoint=1
#   --checkpoint-action=exec=sh exploit.sh
# 這些檔名會被 shell 展開成 tar 的參數,觸發任意指令執行
COPY crontab /etc/cron.d/ais3-backup
RUN chmod 0644 /etc/cron.d/ais3-backup && \
    crontab /etc/cron.d/ais3-backup

COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r//' /entrypoint.sh \
    && chmod +x /entrypoint.sh

EXPOSE 0

ENTRYPOINT ["/entrypoint.sh"]