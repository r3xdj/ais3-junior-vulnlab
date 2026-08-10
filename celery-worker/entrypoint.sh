#!/bin/bash

# 啟動 cron 服務(以 root 身份,Stage 5 提權所需)
service cron start

# 以 celeryuser 身份啟動 Celery Worker(Stage 4 RCE 後拿到的是這個權限)
exec su -s /bin/bash celeryuser -c \
  "celery -A celery_app worker --loglevel=info --queues=celery"