#!/bin/sh

set -e

mkdir -p /home/celeryuser /root

if [ -f /flags/user_flag.txt ]; then
  cp /flags/user_flag.txt /home/celeryuser/user_flag.txt
else
  echo "Flag Error: User flag not found" > /home/celeryuser/user_flag.txt
fi
chown celeryuser:celeryuser /home/celeryuser/user_flag.txt
chmod 644 /home/celeryuser/user_flag.txt

if [ -f /flags/root_flag.txt ]; then
  cp /flags/root_flag.txt /root/root_flag.txt
else
  echo "Flag Error: Root flag not found" > /root/root_flag.txt
fi
chmod 600 /root/root_flag.txt

# 啟動 cron 服務(以 root 身份,Stage 5 提權所需)
service cron start

# 以 celeryuser 身份啟動 Celery Worker(Stage 4 RCE 後拿到的是這個權限)
exec su -s /bin/bash celeryuser -c \
  "celery -A celery_app worker --loglevel=info --queues=celery"