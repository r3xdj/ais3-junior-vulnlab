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
# root 的 shell 環境
# 開 histappend，避免之後手動開互動式 root shell 測試時
# session 結束把下面預先寫好的 .bash_history 蓋掉
# ------------------------------------------------------------

cat > /root/.bashrc << 'EOF'
export HISTFILE=/root/.bash_history
export HISTSIZE=1000
export HISTFILESIZE=2000
shopt -s histappend
EOF

# ------------------------------------------------------------
# root 的 SSH client 設定
# 讓 bash_history 裡挖到的那條 sshpass 指令可以直接重播成功，
# 不會卡在 host key 確認（現實中管理員常見的懶惰設定）
# ------------------------------------------------------------

mkdir -p /root/.ssh
cat > /root/.ssh/config << 'EOF'
Host ingress
    HostName ingress
    User opadmin
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
EOF
chmod 700 /root/.ssh
chmod 600 /root/.ssh/config

# 順手留一則備忘，強化「root 平常真的會手動連 ingress」的敘事，
# 也讓沒仔細翻 .bash_history 的人可以從別的線索找到同一條路
cat > /root/ops-notes.txt << EOF
2026-02 記得每次 log rotate 完要手動上 ingress 確認 apache 有正常重載
帳號 opadmin，密碼問 infra 群組置頂
之後要把這個流程也寫進 crontab 自動化
# Port 22 會被 map 到 2222
EOF
chmod 644 /root/ops-notes.txt


# ------------------------------------------------------------
# 假 bash history
# Stage 6：root 權限取得後發現 SSH 憑證
# ------------------------------------------------------------

cat > /root/.bash_history << EOF
whoami
hostname
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
cd /var/backups
ls -lh
tar -czf celery-logs.tar.gz -C /var/log app
ls -lh celery-logs.tar.gz
cat /root/ops-notes.txt
sshpass -p '${SSH_PIVOT_PASSWORD}' ssh opadmin@ingress
whoami
hostname
pwd
ls -lah
cd /var/log
ls -lah
ps aux | grep ssh
df -h
exit
cd /var/log/app
tail -n 20 celery.log
cd /var/backups
ls -lh
exit
EOF

chmod 600 /root/.bash_history

# 把這幾個檔案的時間戳往前調，避免全部都跟 container 啟動時間一樣新，
# 看起來像是長期累積下來的操作紀錄而不是剛生出來的
touch -d "3 days ago" /root/ops-notes.txt
touch -d "10 days ago" /root/.bashrc /root/.ssh/config
touch -d "1 hour ago" /root/.bash_history


# ------------------------------------------------------------
# 以 celeryuser 身份啟動 Celery Worker
# Stage 4 RCE 後取得的權限為 celeryuser
# ------------------------------------------------------------

exec su -s /bin/bash celeryuser -c \
  "celery -A celery_app worker --loglevel=info --queues=celery"