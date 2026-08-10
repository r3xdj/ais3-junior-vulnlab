# ais3-junior-vulnlab
AIS3 Junior 2026 Project: A custom vulnerable machine designed for CTF/boot2root learning.

## 架構
```
ais3-complex-target-lab/
├── docker-compose.yml
├── .env.example # 環境變數範本 (DB 密碼、Secret Keys 等)
├── ingress/ # 1. 網路入口與邊界層 (Reverse Proxy / Ingress)
│ ├── Dockerfile # 使用具特定 CVE 漏洞的 Apache 版本 (如 2.4.49)
│ ├── httpd.conf # Apache 主設定檔
│ ├── conf.d/ (proxy.conf, site.conf) # 反向代理與虛擬主機設定
│ └── modules/ # 相關載入模組 (如 mod_proxy, mod_cgi)
├── frontend/ # 2. 對外前端服務 (DMZ 區)
│ ├── Dockerfile
│ ├── package.json
│ └── src/ # 前端框架 (React / Vue / HTML)
├── web-gateway/ # 3. 對外 Web 主服務 (DMZ 區)
│ ├── Dockerfile
│ ├── src/ # 包含 Phase 1 ~ Phase N 漏洞邏輯 (app.py, controllers, middleware, utils)
│ └── .git/ # 故意外洩的 Git 版本控管目錄 (Phase 1 偵查)
├── internal-services/ # 4. 內部網路服務區 (Internal Network Zone)
│ ├── auth-service/ # 內網 OAuth / SSO 身分識別服務
│ ├── api-server/ # 核心業務 API (僅限內網 SSRF / 橫向移動目標)
│ └── admin-backend/ # 高權限內部管理後端 (SSRF 利用目標)
├── datastores/ # 5. 資料儲存與快取層 (Database Layer)
│ ├── postgres/ (Dockerfile, init.sql, custom.conf)
│ └── redis/ (Dockerfile, redis.conf) # 快取伺服器 (可作為二次攻擊或 SSRF 利用目標)
├── privilege-escalation/ # 6. 本地提權層 (Privilege Escalation)
│ ├── Dockerfile
│ └── scripts/ (maintenance.sh) # 存在權限漏洞的特權維護腳本
├── flags/ # 7. Flag 管理與動態注入
│ ├── flag_phase1.txt ~ flag_phase4.txt
│ └── deploy_flags.sh # 部署時將 Flag 寫入特定容器或權限目錄
├── docs/ # 8. 專題報告與說明文件 (architecture.png, vulnerability-analysis.md, patch)
└── writeup/ # 9. 解題與 POC 腳本 (README.md, exploit.py)
```

## 技術框架
| 層級 (Layer) | 推薦技術 | 選用原因與特點 |
|---|---|---|
| 容器與編排 | Docker + Docker Compose | 部署方便、環境一致、精準網路隔離（public_net / internal_net）。 |
| 反向代理與邊界入口 | **Apache HTTP Server（含 CVE）** | 作為入口代理，故意配置 CVE（如 CVE-2021-41773）作為 Phase 1–2 初始入侵點。 |
| 對外 Web 後端 | Python Flask | 開發快、無過度封裝，方便自由控制 SSRF（/fetch）與 Session 漏洞點。 |
| 前端 | Jinja2 + Bootstrap 5 | 輕量易維護，可搭配暴露的 `.git` 目錄增加偵查樂趣。 |
| 內網 API 微服務 | Python Flask / FastAPI | 隱藏在 internal_net 的微服務，適合展示內網 SSRF 與未授權 API 存取。 |
| 資料庫 | PostgreSQL / MySQL | 儲存帳號與權限狀態，提供 SQL Injection 或憑證撈取點。 |
| 快取 | Redis | 處理 Session 快取。若未設防護，可透過 SSRF 進行橫向移動或 Key 寫入。 |
| 主機提權 | Linux（Bash Script / SUID） | 配置帶有漏洞的特權腳本（maintenance.sh），實現終極 Root Flag 提權。 |