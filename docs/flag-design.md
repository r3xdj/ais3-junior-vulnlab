# Flag 設計

本靶機共七個 flag，目標不是讓玩家「到處找字串」，而是讓每個 flag 都成為該關卡漏洞利用成功的證明。

| Stage | Flag 位置 | 取得條件 | 為何不會直接跳關 |
|---|---|---|---|
| 1 | `web-gateway/src/flag.txt` | 教材中心 `/api/materials/read` Path Traversal | 只能證明已取得 web-gateway 檔案讀取；Stage 2 仍需理解 JWT/JSON 組裝邏輯 |
| 2 | `GET /api/admin/flag`（回傳值） | 用 JSON injection 取得伺服器簽發的 admin JWT | endpoint 本身不提供 SSRF；Stage 3 仍需另外利用 webhook |
| 3 | Redis key `ctf:flag:stage3` | Admin SSRF + gopher，對 Redis 執行 `GET` | 這個 key 不存在於任何 web API 路由，必須真的透過 gopher 打進內網 Redis 才讀得到 |
| 4 | `/home/celeryuser/user_flag.txt`（celery-worker 容器） | Celery pickle 反序列化 RCE | flag 不在 web-gateway，必須先取得 worker 的 `celeryuser` shell |
| 5 | `/root/root_flag.txt`（celery-worker 容器） | root cron + tar argument injection | root flag 的 seed 只以 root-only 權限掛在 `/root`，`celeryuser` 無法讀取 |
| 6 | `/flag.txt`（ingress 容器，`apache_flag.txt`） | 讀 root 的 `.bash_history` 拿到 SSH 密碼，pivot 進 `opadmin` | 密碼只存在於 Stage 5 拿到的 root shell 之下，且 Stage 4 的 RCE 讀不到（見下方「環境變數」） |
| 7 | `/root/final_flag.txt`（ingress 容器） | `sudo -l` → `NOPASSWD: /usr/bin/vim` → GTFOBins escape | flag 只有 root 可讀，`opadmin` 必須先完成 sudo vim 提權 |

## 原則

### 1. Flag 不應成為下一關的 shortcut

最容易出現的錯誤是把所有 flag 都掛進同一個容器，例如把 `flags/` 整個 bind mount 到 `celery-worker`，Stage 4 RCE 後就能直接讀到 Stage 5 的 root flag，甚至 Stage 6/7 的 ingress flag。

因此目前採用「最小範圍 mount」（見 `docker-compose.yml`）：

```text
flags/user_flag.txt   → celery-worker:/flags/user_flag.txt        (ro)
                         entrypoint 再 chown/cp 給 celeryuser
flags/root_flag.txt   → celery-worker:/root/.root_flag_seed       (ro, root-only)
                         entrypoint 以 root 複製成 /root/root_flag.txt (chmod 600)
flags/apache_flag.txt → ingress:/flag.txt                          (opadmin 可讀)
flags/final_flag.txt  → ingress:/root/final_flag.txt               (ro, root-only)
```

Stage 2 / 3 的 flag 不是檔案，而是由 `.env` 的 `FLAG_STAGE2` / `FLAG_STAGE3` 注入：`FLAG_STAGE2` 由 `/api/admin/flag` 直接回傳；`FLAG_STAGE3` 由同一個 endpoint 寫進 Redis 的 `ctf:flag:stage3`，逼玩家必須真的用 SSRF/gopher 對內網 Redis 下指令才能讀到，而不是重放同一個 HTTP endpoint。

### 2. 每一關的 flag 應與漏洞原語綁定

Flag 位置本身就是 hint，但仍必須完成對應的漏洞利用才能真正讀到：

- traversal → source file
- JSON injection → admin-only endpoint
- SSRF → Redis key（不是 web API）
- pickle RCE → process 使用者的 home 目錄
- tar argument injection → root-only 檔案
- 憑證洩漏 → 另一個容器裡的、對應帳號可讀的檔案
- sudo misconfiguration → root-only 檔案

### 3. 避免環境變數洩漏跳過 Stage 6

`SSH_PIVOT_PASSWORD` 只提供給 `ingress` 與 `celery-worker` 的 root entrypoint。`celery-worker/entrypoint.sh` 在啟動 Celery worker process 前會：

```sh
unset SSH_PIVOT_PASSWORD
```

否則 Stage 4 的任意 Python code execution 可以直接 `os.environ["SSH_PIVOT_PASSWORD"]` 讀到密碼，让 Stage 5（拿 root）與 Stage 6（挖 `.bash_history`）失去意義——玩家會在只有 `celeryuser` 權限時就能 SSH pivot。

### 4. Stage 6 / 7 分開兩個 flag 的理由

如果把 ingress 上唯一的 flag放在 `opadmin` 就能讀到的位置，Stage 7 的 sudo vim LPE 就變成「可做可不做」的加分項，而不是必經步驟。因此刻意拆成：

- `apache_flag.txt`：`opadmin` 可讀，證明 pivot 成功。
- `final_flag.txt`：只有 root 可讀，逼玩家一定要完成 Stage 7 的提權。

## Flag 管理

正式出題時建議只修改：

```text
flags/user_flag.txt
flags/root_flag.txt
flags/apache_flag.txt
flags/final_flag.txt
.env   # FLAG_STAGE2 / FLAG_STAGE3 / SSH_PIVOT_PASSWORD
```

不要把真實 flag 寫進 README、writeup 或 PoC；`writeup/` 底下目前的內容應視為作者驗證用的 exploit script，出題前需要再檢查一次有沒有把正式 flag 寫死進去。
