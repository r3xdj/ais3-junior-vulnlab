# ais3-junior-vulnlab

AIS3 Junior 2026 專題：一台以 Docker Compose 編排、供 CTF / Boot2Root 學習使用的多層自訂靶機。整體以「應用層路徑穿越 → 權限提升 → 內網 SSRF → 反序列化 RCE → 排程提權 → 憑證洩漏橫向移動」六個關卡串成一條完整攻擊鏈，每一層都對應到一個真實世界常見的漏洞類型。漏洞成因與逐關細節整理在 [`docs/vulnerability-analysis.md`](docs/vulnerability-analysis.md)，本文件只涵蓋架構與部署。

## 架構總覽

容器分屬兩個 Docker network：只有 `ingress` 同時掛在 `public_net`（對外開放 `8080`）與 `internal_net`；其餘服務全部只在 `internal_net`（`internal: true`，無法主動連外），選手必須逐層攻陷才能碰到下一層。

```
                                        Player
                                          │  :8080
                                          ▼
                        ┌───────────────────────────────────┐
                        │  ingress (ctf-apache)               │   httpd:2.4.49
                        │  （Stage 6 才會用到：sshd 供橫向回打）│   不作為主線入侵點
                        └───────────────┬───────────┬─────────┘
════════════════════ public_net ═══════│═══════════│═════════════════════════════════
════════════════════ internal_net ═════│═══════════│═════════════════════════════════
                        ProxyPass "/"   │           │ ProxyPass "/api/"
                                        ▼           ▼
                     ┌───────────────────┐   ┌─────────────────────────┐
                     │ frontend :3000     │   │ web-gateway :5000        │
                     │ Flask + Jinja2 頁面殼│──▶│ Flask REST API + JWT 驗證 │
                     └───────────────────┘   │ Stage 1: 教材區 path      │
                                              │ traversal（登入後開放）    │
                                              │ Stage 2: JWT 注入         │
                                              │ Stage 3: admin SSRF       │
                                              └───────────┬───────────────┘
                                                          │
                                    ┌──────────────────────┼───────────────────┐
                                    ▼                                          ▼
                          ┌──────────────────┐                       ┌──────────────────┐
                          │ postgres :5432     │                       │ redis :6379        │
                          │ users /            │                       │ 無密碼、無 port     │
                          │ activity_log       │                       │ 只能靠 SSRF 打進來   │
                          └──────────────────┘                       └─────────┬──────────┘
                                                                                │ LPUSH（gopher SSRF 注入的
                                                                                │ pickle 憑證產生任務）
                                                                                ▼
                                                                     ┌───────────────────────────┐
                                                                     │ celery-worker               │
                                                                     │ Stage 4: pickle RCE          │
                                                                     │ （celeryuser，真實產生 PDF 證書）│
                                                                     │ Stage 5: root cron tar 提權   │
                                                                     │ Stage 6: root .bash_history   │
                                                                     │ 留有 SSH 密碼，可回打 ingress  │
                                                                     └───────────────────────────┘
```

> `image-worker`（ImageMagick 縮圖服務）已規劃整個移除，不再是架構的一部分；正式拆除時記得同步移除 `web-gateway/routes/image.py` 與 `docker-compose.yml` 內對應的 service 區塊。

## 目錄結構

```
ais3-junior-vulnlab/
├── docker-compose.yml            # 服務定義與 public_net / internal_net 網段切分
├── docker-compose.override.yml   # 本機除錯用：額外映射 postgres:5432、redis:6379
├── .env                          # DB 帳密、JWT_SECRET_KEY 等環境變數
│
├── ingress/                      # 1. 入口層 — 唯一對外暴露、跨兩個網段的節點
│   ├── Dockerfile                #    httpd:2.4.49（【待補】加裝 openssh-server 供 Stage 6 SSH 回打）
│   ├── httpd.conf                #    載入 mod_cgi、mod_proxy 等模組
│   ├── conf.d/
│   │   ├── proxy.conf            #    /api/ → web-gateway:5000、/ → frontend:3000
│   │   └── site.conf             #    ScriptAlias /debug 至 cgi-bin/debug.sh（保留但非主線攻擊面）
│   ├── html/index.html           #    Apache 預設頁（掩護用）
│   └── cgi-bin/
│       ├── debug.sh              #    CGI 環境變數輸出（保留，非主線）
│       └── test-cgi.sh           #    最小可用 CGI（whoami / pwd）
│
├── frontend/                     # 2. 對外前端 — 純畫面殼，商業邏輯全部轉呼叫 web-gateway
│   ├── Dockerfile                #    python:3.12-slim
│   └── src/
│       ├── app.py                #    路由 + /api/materials 等反向代理轉接
│       ├── decorators.py         #    頁面層的登入 / 管理員導向判斷
│       ├── static/                #    css/js（common、auth、user、admin、config）
│       └── templates/             #    public/（行銷頁）、user/、admin/、errors/
│
├── web-gateway/                  # 3. API 閘道 — 核心業務邏輯與弱點集中處
│   ├── Dockerfile                #    需要編譯 pycurl，故安裝 build-essential/libcurl
│   └── src/
│       ├── app.py                #    Blueprint 註冊（auth / admin / user / materials）
│       ├── db.py                 #    PostgreSQL 連線池
│       ├── decorators.py         #    require_login / require_admin（JWT 驗證）
│       ├── assets/materials/      #    課程教材（materials.py 供下載）
│       └── routes/
│           ├── auth.py           #    Stage 2：register / login JWT payload 字串串接注入點
│           ├── admin/
│           │   ├── users.py      #    使用者列表 / 角色調整（admin-only）
│           │   └── webhook.py    #    Stage 3：webhook-test / fetch-report SSRF
│           ├── user/              #    profile / password / activity（一般使用者功能）
│           └── materials.py      #    Stage 1：教材下載，path traversal（【待補】需加 @require_login）
│
├── datastores/
│   └── postgres/
│       ├── Dockerfile
│       └── init.sql              #    users / activity_log / materials 資料表
│
├── (redis 服務直接使用官方 redis:7-alpine image，未持久化、未設密碼)
│
├── celery-worker/                # 4-6. 非同步任務層 — RCE、提權與橫向移動的最終落點
│   ├── Dockerfile                #    建立 celeryuser（uid 1000）、安裝 cron、產生世界可寫的 /var/log/app
│   ├── crontab                   #    Stage 5：root 身份、每分鐘對 /var/log/app/* 執行 tar（萬用字元注入點）
│   ├── entrypoint.sh             #    寫入 flags、啟動 cron、以 celeryuser 啟動 celery worker
│   │                              #    【待補】啟動時寫入 root 的 .bash_history（Stage 6 SSH 密碼線索）
│   └── src/
│       ├── celery_app.py         #    task_serializer='pickle' → Redis 佇列可被注入任意反序列化 payload
│       └── tasks.py              #    Stage 4：generate_certificate（【待補】改為真實 PDF + 雷達圖產生）
│
├── flags/
│   ├── user_flag.txt             #    Stage 4 落地權限（celeryuser）取得
│   └── root_flag.txt             #    Stage 5 完成提權（root）取得
│
├── docs/
│   └── vulnerability-analysis.md #    完整攻擊鏈與逐關漏洞成因說明
└── writeup/PoC/
    └── gopher_rce_poc.py         #    Stage 2→3→4 串接 PoC：偽造 admin JWT → SSRF(gopher) → Redis LPUSH pickle task → RCE
```

## 技術框架

| 層級 (Layer) | 技術 | 選用原因與特點 |
|---|---|---|
| 容器與編排 | Docker + Docker Compose | 部署方便、環境一致，並以 `public_net` / `internal_net` 精準做網路隔離。 |
| 反向代理與邊界入口 | Apache HTTP Server 2.4.49（`ingress`） | 唯一對外容器；不再作為主線入侵點，僅在 Stage 6 作為 SSH 橫向移動的落點。 |
| 對外前端 | Python Flask + Jinja2（`frontend`） | 純畫面殼，邏輯全轉呼叫 `web-gateway`，降低前端本身的攻擊面複雜度。 |
| API 閘道 | Python Flask（`web-gateway`） | 承載認證、JWT 簽發、管理端點、教材下載與 SSRF 弱點，是整條攻擊鏈的核心。 |
| 資料庫 | PostgreSQL（`datastores/postgres`） | 儲存帳號、角色與活動紀錄。 |
| 佇列 / 快取 | Redis 7（官方 image） | 無密碼、無對外 port，只能透過 SSRF 觸及，作為 Stage 3→4 的橋樑。 |
| 非同步任務 | Celery 5（`celery-worker`） | 開啟 pickle 序列化，未來承載真實 PDF 憑證產生功能，也是 Stage 4 反序列化 RCE 弱點來源。 |
| 主機提權 | cron + `tar`（`celery-worker` 內） | root 排程搭配世界可寫目錄，示範 `tar` 萬用字元注入提權（Stage 5）。 |
| 橫向移動 | OpenSSH（`ingress`，待補） | root 的 `.bash_history` 洩漏 SSH 密碼，示範憑證外洩導致的內網跳板（Stage 6）。 |

## 環境變數（`.env`）

| 變數 | 用途 |
|---|---|
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | PostgreSQL 帳密，供 `postgres` 與 `web-gateway` 使用 |
| `JWT_SECRET_KEY` | `web-gateway` 簽發 / 驗證 JWT、`frontend` 頁面層驗證使用 |
| `REDIS_HOST` / `REDIS_PORT` | `web-gateway`、`celery-worker` 連線 Redis 使用 |

`docker-compose.override.yml` 僅供本機除錯：額外映射 `postgres:5432`、`redis:6379` 到主機，方便直接以 `psql` / `redis-cli` 檢查狀態，正式部署時應移除或不套用。

## 啟動

```bash
docker compose up -d --build
```

然後訪問 http://localhost:8080

## 關閉

```bash
docker compose down -v
```

記得加上 `-v` 才會清除資料庫 volume（`pgdata`）。
