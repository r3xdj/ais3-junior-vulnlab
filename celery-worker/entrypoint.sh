#!/bin/sh

set -e

mkdir -p \
  /home/celeryuser \
  /root \
  /var/backups \
  /var/log/app

# ------------------------------------------------------------
# User flag
# ------------------------------------------------------------

if [ -f /flags/user_flag.txt ]; then
  cp /flags/user_flag.txt /home/celeryuser/user_flag.txt
else
  echo "Flag Error: User flag not found" > /home/celeryuser/user_flag.txt
fi

chown celeryuser:celeryuser /home/celeryuser/user_flag.txt
chmod 644 /home/celeryuser/user_flag.txt


# ------------------------------------------------------------
# Root flag
# ------------------------------------------------------------

if [ -f /flags/root_flag.txt ]; then
  cp /flags/root_flag.txt /root/root_flag.txt
else
  echo "Flag Error: Root flag not found" > /root/root_flag.txt
fi

chmod 600 /root/root_flag.txt


# ------------------------------------------------------------
# Application log
# ------------------------------------------------------------

touch /var/log/app/celery.log
chown celeryuser:celeryuser /var/log/app/celery.log
chmod 664 /var/log/app/celery.log

echo "$(date '+%Y-%m-%d %H:%M:%S') celery-worker container started" \
  >> /var/log/app/celery.log


# ------------------------------------------------------------
# Backup directory
# ------------------------------------------------------------

touch /var/backups/.keep
chmod 644 /var/backups/.keep


# ------------------------------------------------------------
# 啟動 cron
# root 身份啟動，Stage 5 提權所需
# ------------------------------------------------------------

service cron start


# ------------------------------------------------------------
# 建立一個合理的歷史備份檔
# ------------------------------------------------------------

tar -czf /var/backups/celery-logs.tar.gz \
  -C /var/log app


# ------------------------------------------------------------
# 假 bash history
# Stage 6：root 權限取得後發現 SSH 憑證
# ------------------------------------------------------------

cat > /root/.bash_history << EOF
# From Host, the port 22 will be mapped to 2222
cd /var/log/app
ls -lah
tail -n 50 celery.log
cd /var/backups
ls -lah
du -sh *
ps aux | grep celery
ps aux | grep cron
crontab -l
cd /var/log/app
tail -n 100 celery.log
sshpass -p '${SSH_PIVOT_PASSWORD}' ssh opadmin@ingress
cd /var/backups
ls -lh
tar -czf celery-logs.tar.gz -C /var/log app
ls -lh celery-logs.tar.gz
exit
EOF

chmod 600 /root/.bash_history


# ------------------------------------------------------------
# 以 celeryuser 身份啟動 Celery Worker
# Stage 4 RCE 後取得的權限為 celeryuser
# ------------------------------------------------------------

exec su -s /bin/bash celeryuser -c \
  "celery -A celery_app worker --loglevel=info --queues=celery"