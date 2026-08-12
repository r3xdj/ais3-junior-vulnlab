#!/bin/sh
echo "opadmin:${SSH_PIVOT_PASSWORD}" | chpasswd
/usr/sbin/sshd
exec httpd-foreground