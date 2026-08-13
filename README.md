# ais3-junior-vulnlab

AIS3 Junior 2026 自製 CTF / Boot2Root 靶機。

這台靶機不是單一漏洞，而是一條刻意串接的七階段攻擊鏈：

```text
Stage 1  教材中心 Path Traversal            → 讀取 web-gateway 原始碼
Stage 2  註冊頁面 JSON Injection            → 取得伺服器簽發的 admin JWT
Stage 3  Admin Webhook SSRF (gopher)        → 打進內網 Redis
Stage 4  Celery Pickle 反序列化              → celeryuser RCE
Stage 5  root cron + tar Argument Injection → celeryuser 提權為 root
Stage 6  root .bash_history 洩漏 SSH 密碼    → pivot 進 ingress (opadmin)
Stage 7  sudo -l 允許以 root 執行 vim         → opadmin 提權為 root
```

每一關都有一個 flag，flag 的位置與該關取得的 primitive 綁定，不把整個 `flags/` 目錄直接暴露給玩家。

> 本 README 是部署與架構文件；漏洞成因、逐關驗證步驟與 flag 設計請看 `docs/`。

## 1. 架構

```text
                         Player
                           │
                           │ TCP/8080 (HTTP)  TCP/2222 (SSH, Stage 6 之後才需要)
                           ▼
                  ┌────────────────────┐
                  │ ingress / Apache    │
                  │ :80, :22            │
                  │ Stage 6–7 target    │
                  └─────────┬──────────┘
                             │
                     public_net + internal_net
                             │
             ┌───────────────┴───────────────┐
             ▼                               ▼
      ┌──────────────┐                ┌──────────────┐
      │ frontend     │                │ web-gateway  │
      │ :3000        │───────────────▶│ :5000        │
      │ UI           │                │ Stage 1–3    │
      └──────────────┘                └──────┬───────┘
                                              │
                                  ┌───────────┴───────────┐
                                  ▼                       ▼
                           ┌────────────┐          ┌────────────┐
                           │ PostgreSQL │          │ Redis      │
                           │ :5432      │          │ :6379      │
                           └────────────┘          └─────┬──────┘
                                                          │ broker
                                                          ▼
                                                   ┌──────────────┐
                                                   │ celery-worker │
                                                   │ celeryuser    │
                                                   │ Stage 4–5     │
                                                   └──────┬───────┘
                                                          │
                                                          │ SSH pivot (Stage 6)
                                                          ▼
                                                   ┌──────────────┐
                                                   │ ingress      │
                                                   │ opadmin      │
                                                   │ Stage 6–7    │
                                                   └──────────────┘
```

### Network

- `public_net`：玩家可經 Apache / frontend / web-gateway 到達的邊界網路。
- `internal_net`：PostgreSQL、Redis、celery-worker 與 ingress 的內部網路（`internal: true`，不提供對外連線）。
- `ingress` 同時掛在 `public_net` 與 `internal_net`，是唯一橋接兩個網路的容器。
- Apache 對 host publish `8080:80` 與 `2222:22`；玩家在 Stage 6 取得 `opadmin` 密碼前無法真正利用 SSH 埠。

## 2. 攻擊鏈

| Stage | 漏洞 | 玩家得到的能力 | Flag |
|---|---|---|---|
| 1 | `/api/materials/read` Path Traversal | 讀取 web-gateway 原始碼（`auth.py`、`webhook.py`、`celery_app.py` 等） | `web-gateway/src/flag.txt` |
| 2 | 註冊 / 登入時字串拼接 JSON → JWT | 伺服器簽發的合法 admin JWT | `GET /api/admin/flag` |
| 3 | Admin webhook-test SSRF（`pycurl` 支援 `gopher://`） | 對內網 Redis 下任意 RESP 指令 | Redis key `ctf:flag:stage3` |
| 4 | Celery `task_serializer=pickle` 反序列化 | `celeryuser` 任意程式碼執行 | `/home/celeryuser/user_flag.txt` |
| 5 | root cron 對 world-writable 目錄執行 `tar -czf ... *` | root（celery-worker 容器內） | `/root/root_flag.txt` |
| 6 | root 的 `.bash_history` 內含明文 SSH pivot 密碼 | SSH 登入 ingress 的 `opadmin` | `/flag.txt`（ingress，`apache_flag.txt`） |
| 7 | `opadmin` 的 sudoers 允許 `NOPASSWD: /usr/bin/vim` | ingress 上的 root（GTFOBins `vim` escape） | `/root/final_flag.txt`（ingress） |

詳細設計：

- `docs/vulnerability-analysis.md` — 逐關漏洞成因與利用原理
- `docs/flag-design.md` — 七關 flag 的位置、掛載方式與防跳關設計
- `docs/deployment.md` — 部署、逐關驗證步驟與作者驗收表
- `docs/remediation.md` — 七個漏洞各自的修補建議（root cause fix + 縱深防禦）

## 3. 主要服務

| Service | 技術 | 角色 |
|---|---|---|
| `apache` (ingress) | Apache HTTP Server 2.4.49 + OpenSSH + sudo | public ingress；反向代理到 frontend / web-gateway；Stage 6–7 target |
| `frontend` | Flask + Jinja2 | 使用者介面 |
| `web-gateway` | Flask + PostgreSQL + Redis client | 帳號、教材、Admin API；Stage 1–3 |
| `redis` | Redis 7 (alpine) | Stage 3 SSRF 目標 / Stage 4 Celery broker |
| `postgres` | PostgreSQL | 帳號、活動紀錄、證書資料 |
| `celery-worker` | Celery + pickle serializer | Stage 4 RCE（`celeryuser`）/ Stage 5 root 提權（cron） |

`ingress/cgi-bin`、`ingress/conf.d` 中的 CGI 除錯腳本與 Apache 2.4.49 版本僅用於維持「舊版靶機」的場景感，**不是**目前主線攻擊鏈的入口；真正的入口是 Stage 1 的 path traversal。

## 4. 證書功能

證書流程是靶機的正常業務背景，也是 Celery / pickle 存在的合理理由：

1. Admin 為一般成員登記成績。
2. 系統建立 `pending` certificate。
3. Celery worker 產生 PDF 與技能雷達圖（Matplotlib `Figure` 物件無法用 JSON 序列化，因此業務上「需要」pickle）。
4. Worker 更新狀態為 `issued`。
5. 一般成員下載自己的證書。

## 5. Flag 設計摘要

不要把整個：

```text
./flags:/flags:ro
```

掛進 `celery-worker`，否則 Stage 4 RCE 可以直接 `cat /flags/root_flag.txt` 跳過 Stage 5。

目前採最小掛載（詳見 `docs/flag-design.md`）：

```text
flags/user_flag.txt  → celery-worker 的 /flags/user_flag.txt（唯讀，entrypoint 再複製給 celeryuser）
flags/root_flag.txt  → celery-worker 的 /root/.root_flag_seed（root-only，唯讀）
flags/apache_flag.txt → ingress 的 /flag.txt（opadmin 可讀）
flags/final_flag.txt → ingress 的 /root/final_flag.txt（root-only，唯讀）
```

`SSH_PIVOT_PASSWORD` 在 celery-worker 啟動 Celery 前會被 `unset`，避免 Stage 4 的任意 Python code execution 直接從環境變數讀到 Stage 6 的密碼。

## 6. 環境變數

`.env` 至少需要：

```dotenv
DB_NAME=app_db
DB_USER=app_user
DB_PASSWORD=change-me
JWT_SECRET_KEY=change-me
REDIS_HOST=redis
REDIS_PORT=6379

FLAG_STAGE2=AIS3{...}
FLAG_STAGE3=AIS3{...}

SSH_PIVOT_PASSWORD=change-me
```

`FLAG_STAGE2`、`FLAG_STAGE3` 與 `SSH_PIVOT_PASSWORD` 不應提交到公開 repository；`run.sh` 會在每次啟動時以 `openssl rand` 重新產生 `DB_PASSWORD` / `JWT_SECRET_KEY` / `SSH_PIVOT_PASSWORD`。

## 7. 啟動

```bash
./run.sh -d --build
```

瀏覽：

```text
http://localhost:8080
```

## 8. 停止與重置

停止：

```bash
docker compose down
```

完整重置資料庫與 volumes：

```bash
docker compose down -v
```

重新 build：

```bash
./run.sh -d --build
```

## 9. 開發者注意事項

### `docker-compose.override.yml`

Override 會 publish：

```text
5432:5432
6379:6379
```

只適合本機開發與 debug，正式出題不要使用它。

### Apache / ingress

- Apache 保留 `2.4.49` 只是維持場景感，不是主線入口。
- `2222:22` 對 host 開放，但沒有密碼就無法登入；密碼只存在於 Stage 5 拿到的 root 之下的 `.bash_history`。
- `opadmin` 的 sudoers 只允許 `NOPASSWD: /usr/bin/vim`，這是 Stage 7 的 LPE 入口（GTFOBins）。

### Celery

`pickle` 序列化是刻意的漏洞，不要在正式環境照搬。

### cron

`tar -czf ... *`（對 world-writable 目錄的萬用字元展開）是刻意保留的 argument injection 教學點。

## 10. 目錄

```text
ais3-junior-vulnlab/
├── docker-compose.yml
├── docker-compose.override.yml
├── .env
├── .env.example
├── run.sh
│
├── ingress/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── httpd.conf
│   ├── conf.d/
│   └── cgi-bin/
│
├── frontend/
│   └── src/
│
├── web-gateway/
│   └── src/
│       ├── app.py
│       ├── db.py
│       ├── decorators.py
│       ├── certificate_service.py
│       ├── flag.txt              # Stage 1 flag
│       ├── assets/materials/     # Stage 1 traversal 起點
│       └── routes/
│           ├── auth.py           # Stage 2
│           ├── materials.py      # Stage 1
│           ├── admin/
│           │   ├── webhook.py    # Stage 3
│           │   ├── flags.py
│           │   └── users.py
│           └── user/
│
├── datastores/
│   └── postgres/
│
├── celery-worker/
│   ├── Dockerfile
│   ├── crontab                   # Stage 5
│   ├── entrypoint.sh             # Stage 5–6 布置
│   └── src/
│       ├── celery_app.py         # Stage 4 (pickle)
│       └── tasks.py
│
├── flags/
│   ├── user_flag.txt
│   ├── root_flag.txt
│   ├── apache_flag.txt
│   └── final_flag.txt
│
├── docs/
│   ├── vulnerability-analysis.md
│   ├── flag-design.md
│   ├── deployment.md
│   └── remediation.md
│
└── writeup/
    ├── PoC/
    └── exploit/
```
