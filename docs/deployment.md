# 部署與測試

## 啟動

第一次啟動：

```bash
./run.sh -d --build
```

`run.sh` 會用 `openssl rand` 重新產生 `DB_PASSWORD` / `JWT_SECRET_KEY` / `SSH_PIVOT_PASSWORD`，並在啟動前 `docker compose down -v` 清空舊資料。

入口：

```text
http://localhost:8080
```

正式 challenge 不要套用 `docker-compose.override.yml`，因為它會把 PostgreSQL / Redis 直接 publish 到 host（`5432:5432`、`6379:6379`），繞過所有需要 SSRF 才能碰到內網服務的關卡設計。

## 完整測試順序

### Stage 1 — Path Traversal

1. 建立一般帳號並登入。
2. 進教材中心頁面。
3. 對 `POST /api/materials/read` 的 `file` 欄位送出相對路徑（例如 `../routes/auth.py`）。
4. 確認能讀到 `web-gateway/src/flag.txt`。
5. 確認 `routes/auth.py`、`routes/admin/webhook.py`、`celery_app.py`（若同一 volume 可觸及）可被讀取，作為後續關卡的情報來源。

### Stage 2 — JSON Injection → Admin JWT

1. 用 Stage 1 取得的原始碼確認 `register()` 的 JWT payload 是用字串拼接組出來的。
2. 註冊一個 `username` 帶有 `"`、`,` 等 JSON 語法字元，讓拼接後的 JSON 多出 `"role": "admin"`。
3. 確認拿到的 `session_token` cookie 解碼後 `role` 為 `admin`。
4. 呼叫 `GET /api/admin/flag`，應取得 Stage 2 flag，且 Redis 應同時出現 `ctf:flag:stage3`。

### Stage 3 — SSRF + Gopher → Redis

1. 用 admin JWT 呼叫 `/api/admin/webhook-test`，`url` 帶 `gopher://redis:6379/...`。
2. 組出的 gopher payload 應能對內網 Redis 送出 RESP 指令。
3. 至少驗證 `GET ctf:flag:stage3` 能透過這條路徑取得 Stage 3 flag。

### Stage 4 — Celery Pickle RCE

1. 用同一條 gopher SSRF，對 Redis 執行 `LPUSH celery <偽造的 pickle 訊息>`。
2. 等待 celery-worker 消費該訊息並反序列化。
3. 確認取得的 shell `id -un` 為 `celeryuser`。
4. 確認可讀到 `/home/celeryuser/user_flag.txt`。

### Stage 5 — cron + tar Argument Injection

1. 以 Stage 4 的 RCE，在 `/var/log/app` 建立形如 `--checkpoint=1`、`--checkpoint-action=exec=sh shell.sh` 的檔名與對應 payload。
2. 等待 root cron（每分鐘執行一次）。
3. 確認 payload 執行後的身分為 `root`（可用寫入檔案、起 reverse shell 等方式驗證）。
4. 確認可讀到 `/root/root_flag.txt`。

### Stage 6 — 憑證洩漏 + SSH Pivot

1. 以 Stage 5 拿到的 root，`cat /root/.bash_history`（必要時也檢查 `/root/ops-notes.txt`）。
2. 從中找出 `sshpass -p '<password>' ssh opadmin@ingress`。
3. 從 celery-worker（或 host 的 `2222` port）以該密碼 SSH 登入 `opadmin@ingress`。
4. 確認 `id` 顯示為 `opadmin`。
5. 確認可讀到 `/flag.txt`（Stage 6 flag）。

### Stage 7 — sudo vim LPE

1. 以 `opadmin` 身分執行 `sudo -l`，確認只有 `(root) NOPASSWD: /usr/bin/vim`。
2. 執行 `sudo vim -c ':!/bin/sh'`（或互動輸入 `:!/bin/sh`）取得 root shell。
3. 確認 `id` 顯示為 `root`。
4. 確認可讀到 `/root/final_flag.txt`（最終 flag）。

## 重建

如果測試過程動到 root filesystem 或資料庫狀態，建議：

```bash
docker compose down -v
./run.sh -d --build
```

## 作者驗收表

- [ ] Host 只有 `8080/tcp`（HTTP）與 `2222/tcp`（SSH，需密碼）對外，沒有其他非預期 port。
- [ ] 未套用 `docker-compose.override.yml` 時，Redis / PostgreSQL 沒有直接 publish 到 host。
- [ ] Stage 1 flag 只能透過 `/api/materials/read` 的 traversal 取得，前端 UI 不會直接列出。
- [ ] Stage 2 flag 需要先完成 JSON injection 拿到 admin JWT，未登入 / 一般使用者呼叫 `/api/admin/flag` 應回 401/403。
- [ ] Stage 3 flag 位於 Redis key，不存在於任何 web API 回應中。
- [ ] Stage 4 `user_flag.txt` 不需要 root 權限即可讀取（`celeryuser` 可讀）。
- [ ] Stage 5 `root_flag.txt` 的 seed（`/root/.root_flag_seed`）`celeryuser` 讀不到。
- [ ] Stage 4 的 RCE（`celeryuser` 環境）讀不到 `SSH_PIVOT_PASSWORD`（已在啟動 worker 前 `unset`）。
- [ ] `/root/.bash_history`、`/root/ops-notes.txt` 內的密碼與正式出題的 `SSH_PIVOT_PASSWORD` 一致。
- [ ] Stage 6 flag（`/flag.txt`）`opadmin` 可讀，但一般玩家在沒有密碼前無法登入 SSH。
- [ ] `opadmin` 的 `sudo -l` 只列出 `/usr/bin/vim`，沒有其他多餘的 NOPASSWD 項目。
- [ ] Stage 7 flag（`/root/final_flag.txt`）只有 root 可讀，`opadmin` 直接 `cat` 應該失敗。
- [ ] `flags/` 目錄未被整包掛進任何容器（逐一檢查 `docker-compose.yml` 的 volumes）。
- [ ] `.env` 內的 `FLAG_STAGE2`、`FLAG_STAGE3`、`SSH_PIVOT_PASSWORD`、`DB_PASSWORD`、`JWT_SECRET_KEY` 在正式出題前已更換，且未提交到公開 repository。
