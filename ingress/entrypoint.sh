#!/bin/sh

set -eu

# ------------------------------------------------------------
# Apache flag
# ------------------------------------------------------------

chown opadmin:opadmin /flag.txt
chmod 644 /flag.txt

echo "opadmin:${SSH_PIVOT_PASSWORD}" | chpasswd
/usr/sbin/sshd
exec httpd-foreground