# Flag 設計

本靶機共六個 flag，目標不是讓玩家「到處找字串」，而是讓每個 flag 都成為該關卡原語成功的證明。

| Stage | Flag 位置 | 取得條件 | 為何不會直接跳關 |
|---|---|---|---|
| 1 | `web-gateway/src/stage1_flag.txt` | 教材 API Path Traversal | 只能證明已取得 web-gateway 檔案；Stage 2 仍需理解 JWT 建構 |
| 2 | `GET /api/admin/flag` | 取得合法 admin JWT | endpoint 本身不提供 SSRF；Stage 3 仍需利用 webhook |
| 3 | Redis `ctf:flag:stage3` | Admin SSRF + gopher + Redis GET | Redis key 不存在於 web API 路由，必須真的打進內網 Redis |
| 4 | `/home/celeryuser/user_flag.txt` | Celery Pickle RCE | flag 不在 web-gateway；必須取得 worker 的 `celeryuser` |
| 5 | `/root/root_flag.txt` | cron + tar argument injection | root seed 位於 `/root`，worker 使用者無法讀取 |
| 6 | `/root/final_flag.txt`（ingress） | opadmin → Apache root CGI LPE | flag 受 `/root` 權限保護，只能由 root CGI 讀取 |

## 原則

### 1. Flag 不應成為下一關的 shortcut

最容易出現的錯誤是把所有 flag 都掛進同一個容器。例如把 `flags/` 整個 bind mount 到 `celery-worker`，Stage 4 RCE 後就能直接讀到 Stage 5 root flag。

因此目前採用「最小範圍 mount」：

- user flag → worker 可讀位置
- root flag → `/root` 下的 root-only seed
- Stage 6 flag → ingress 的 `/root`
- Stage 2 / 3 → application / Redis primitive

### 2. 每一關的 flag 應與漏洞原語綁定

Flag 位置本身就是 hint：

- traversal → source file
- JWT privilege escalation → admin endpoint
- SSRF → Redis key
- RCE → process user home
- LPE → root-only file

玩家不需要猜「下一關 flag 藏在哪」，但仍必須完成漏洞利用。

### 3. Stage 6 特別避免環境變數洩漏

`SSH_PIVOT_PASSWORD` 只提供給 `ingress` 與 worker 的 root entrypoint。

worker 在啟動 Celery 前會：

```sh
unset SSH_PIVOT_PASSWORD
```

否則 Stage 4 的任意 Python code execution 可以直接：

```python
os.environ["SSH_PIVOT_PASSWORD"]
```

這會讓 Stage 5 / 6 的設計失去意義。

## Flag 管理

正式出題時建議只修改：

```text
flags/user_flag.txt
flags/root_flag.txt
flags/final_flag.txt
.env
```

Stage 2 / 3 的 flag 則由 `.env` 注入：

```text
FLAG_STAGE2=...
FLAG_STAGE3=...
```

不要把真實 flag 寫進 README、writeup 或 PoC。
