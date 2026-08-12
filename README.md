# ais3-junior-vulnlab

AIS3 Junior 2026 自製 CTF / Boot2Root 靶機。

這台靶機不是單一漏洞，而是一條刻意串接的多階段攻擊鏈：

```text
教材中心 Path Traversal
        ↓
JWT JSON Injection → Admin
        ↓
Admin SSRF / Gopher → Redis
        ↓
Celery Pickle RCE → celeryuser
        ↓
cron + tar Argument Injection → root
        ↓
root .bash_history 洩漏 SSH credentials
        ↓
SSH → ingress / opadmin
        ↓
Apache conf + CGI writable + sudo restart
        ↓
Apache root CGI → Stage 6
```

每一關都有一個 flag，而且 flag 的位置與該關取得的 primitive 綁定，不把整個 `flags/` 目錄直接暴露給玩家。

> 本 README 是部署與架構文件；漏洞成因、Stage 6 LPE 與 flag 設計請看 `docs/`。

## 1. 架構

```text
                         Player
                           │
                           │ TCP/8080
                           ▼
                  ┌───────────────────┐
                  │ ingress / Apache   │
                  │ :80                │
                  │ Stage 6 SSH target │
                  └─────────┬─────────┘
                            │
                    public_net + internal_net
                            │
             ┌──────────────┴──────────────┐
             ▼                             ▼
      ┌──────────────┐              ┌──────────────┐
      │ frontend     │              │ web-gateway  │
      │ :3000        │─────────────▶│ :5000        │
      │ UI           │              │ Stage 1–3    │
      └──────────────┘              └──────┬───────┘
                                          │
                              ┌───────────┴───────────┐
                              ▼                       ▼
                       ┌────────────┐          ┌────────────┐
                       │ PostgreSQL │          │ Redis      │
                       │ :5432      │          │ :6379      │
                       └────────────┘          └─────┬──────┘
                                                    │
                                                    ▼
                                             ┌──────────────┐
                                             │ celery-worker │
                                             │ celeryuser    │
                                             │ Stage 4–5     │
                                             └──────┬───────┘
                                                    │
                                                    │ SSH pivot
                                                    ▼
                                             ┌──────────────┐
                                             │ ingress      │
                                             │ opadmin      │
                                             │ Stage 6      │
                                             └──────────────┘
```

### Network

- `public_net`：玩家可經 Apache / frontend / web-gateway 到達的邊界網路。
- `internal_net`：PostgreSQL、Redis、Celery worker 與 ingress 的內部網路。
- `internal_net` 設為 Docker `internal: true`，不提供一般外連能力。
- Apache **只 publish `8080:80`**；SSH 22 不 publish 到 host。

## 2. 攻擊鏈

| Stage | 漏洞 | 玩家得到的能力 | Flag |
|---|---|---|---|
| 1 | 教材 API Path Traversal | 讀取 web-gateway source | `web-gateway/src/stage1_flag.txt` |
| 2 | JWT JSON injection | 合法 admin JWT | `/api/admin/flag` |
| 3 | Admin SSRF + gopher | 操作 internal Redis | `ctf:flag:stage3` |
| 4 | Celery pickle deserialization | `celeryuser` RCE | `/home/celeryuser/user_flag.txt` |
| 5 | root cron + tar wildcard | root | `/root/root_flag.txt` |
| 6 | SSH credential leak + Apache LPE | ingress root CGI | `/root/final_flag.txt` |

詳細設計：

- `docs/vulnerability-analysis.md` — 完整攻擊鏈與漏洞成因
- `docs/flag-design.md` — 六關 flag 的位置與防跳關設計
- `docs/deployment.md` — 部署、測試與作者驗收表

## 3. 主要服務

| Service | 技術 | 角色 |
|---|---|---|
| `apache` | Apache HTTP Server 2.4.49 + OpenSSH | public ingress；Stage 6 target |
| `frontend` | Flask + Jinja2 | 使用者介面 |
| `web-gateway` | Flask + PostgreSQL + Redis client | Stage 1–3 |
| `redis` | Redis 7 | Stage 3 internal target / Stage 4 broker |
| `postgres` | PostgreSQL | 帳號、活動與證書資料 |
| `celery-worker` | Celery + ReportLab + Matplotlib | Stage 4 RCE / Stage 5 LPE |

## 4. 證書功能

證書流程仍是靶機的正常業務背景：

1. Admin 為一般成員登記五項成績。
2. 系統建立 `pending` certificate。
3. Celery 產生 PDF 與 skill radar chart。
4. Worker 更新狀態為 `issued`。
5. 一般成員下載自己的證書。

這個業務流程提供 Celery queue 的合理存在理由，也讓 Stage 4 的 pickle serializer 有「看似合理」的背景。

## 5. Flag 設計

不要把：

```text
./flags:/flags:ro
```

整個目錄掛入 worker。

這會讓 Stage 4 RCE 直接：

```text
cat /flags/root_flag.txt
```

跳過 Stage 5。

目前採最小掛載：

```text
user_flag.txt → worker 的 /flags/user_flag.txt
root_flag.txt → worker 的 /root/.root_flag_seed
final_flag.txt → ingress 的 /root/final_flag.txt
```

其中 root-only mount 都位於 `/root`，並由 container entrypoint / Apache root CGI 使用。

另外，Stage 4 的 Celery process **不繼承 `SSH_PIVOT_PASSWORD`**，避免玩家用任意 Python code execution 直接讀環境變數跳到 Stage 6。

## 6. 環境變數

`.env` 至少需要：

```dotenv
DB_NAME=app_db
DB_USER=app_user
DB_PASSWORD=change-me
JWT_SECRET_KEY=change-me
REDIS_HOST=redis
REDIS_PORT=6379

FLAG_STAGE2=AIS3{stage2_jwt_admin}
FLAG_STAGE3=AIS3{stage3_ssrf_redis}

SSH_PIVOT_PASSWORD=change-me
```

`FLAG_STAGE2` 與 `FLAG_STAGE3` 不應提交到公開 repository。

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

只適合本機開發與 debug。

正式出題不要使用它。

### Apache

Apache 保留 `2.4.49` 是為了維持靶機場景感，但 CVE 不屬於主線入口。

Stage 6 的 Apache 弱點是：

```text
opadmin
  ├── writable conf.d
  ├── writable cgi-bin
  └── sudo httpd -k restart
```

三者組合造成 root CGI execution。

### Celery

`pickle` 是刻意的漏洞，不要在正式環境照搬。

### cron

`tar *` 是刻意保留的 argument injection 教學點。

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
│   ├── cgi-bin/
│   └── sudoers.d/
│
├── frontend/
├── web-gateway/
│   └── src/
│       ├── routes/
│       └── stage1_flag.txt
│
├── datastores/
│   └── postgres/
│
├── celery-worker/
│   ├── Dockerfile
│   ├── crontab
│   ├── entrypoint.sh
│   └── src/
│
├── flags/
│   ├── user_flag.txt
│   ├── root_flag.txt
│   └── final_flag.txt
│
├── docs/
│   ├── vulnerability-analysis.md
│   ├── flag-design.md
│   └── deployment.md
│
└── writeup/
    ├── PoC/
    └── exploit/
```
