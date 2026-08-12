# 部署與測試

## 啟動

第一次啟動：

```bash
./run.sh -d --build
```

入口：

```text
http://localhost:8080
```

正式 challenge 不要套用 `docker-compose.override.yml`，因為 override 會把 PostgreSQL / Redis publish 到 host。

## 完整測試順序

### Stage 1

1. 建立一般帳號。
2. 登入。
3. 進教材中心。
4. 使用 `/api/materials/read` 的 `file` 欄位做 traversal。
5. 確認能讀到 `web-gateway/src/stage1_flag.txt`。
6. 確認 `routes/auth.py` 與 `routes/admin/webhook.py` 可被讀取。

### Stage 2

使用 Stage 1 取得的 source 找出 JWT construction。

確認：

```text
normal user → injected username → server-signed admin JWT
```

再呼叫：

```text
GET /api/admin/flag
```

應取得 Stage 2 flag。

### Stage 3

從 admin webhook 對：

```text
gopher://redis:6379/...
```

送 Redis RESP。

至少驗證：

```text
GET ctf:flag:stage3
```

能取得 Stage 3 flag。

### Stage 4

使用 gopher 對 Redis `LPUSH celery` 注入 Celery pickle task。

成功後：

```text
id -un
```

應為：

```text
celeryuser
```

並可讀：

```text
/home/celeryuser/user_flag.txt
```

### Stage 5

以 Stage 4 RCE 建立 tar wildcard payload。

等待 root cron：

```text
每分鐘一次
```

成功後確認：

```text
id
cat /root/root_flag.txt
```

### Stage 6

root shell：

```text
cat /root/.bash_history
```

找出 pivot credentials。

從 worker：

```text
ssh opadmin@ingress
```

登入後確認：

```text
id
```

應為：

```text
uid=... (opadmin)
```

接著：

1. 建立惡意 CGI。
2. 建立 Apache config override。
3. `sudo /usr/local/apache2/bin/httpd -k restart`
4. 透過 `/cgi-bin/...` 執行 root CGI。
5. 讀取 `/root/final_flag.txt`。

## 重建

如果測試過 root filesystem 或資料庫狀態，建議：

```bash
docker compose down -v
./run.sh -d --build
```

## 作者驗收表

- [ ] Host 只有 `8080/tcp` 對外。
- [ ] Redis / PostgreSQL 沒有正式 publish。
- [ ] Stage 1 flag 只能透過 traversal 取得。
- [ ] Stage 2 flag 需要 admin JWT。
- [ ] Stage 3 flag 位於 Redis。
- [ ] Stage 4 user flag 不需要 root。
- [ ] Stage 5 root flag 不可由 celeryuser 讀取。
- [ ] Stage 4 RCE 讀不到 `SSH_PIVOT_PASSWORD`。
- [ ] Stage 6 SSH 只能由 internal network 使用。
- [ ] opadmin 可以寫 Apache conf / CGI。
- [ ] opadmin 不能直接 `sudo sh`。
- [ ] Stage 6 CGI 可以 root 身份執行。
- [ ] Stage 6 flag 只有 root CGI 能讀。
