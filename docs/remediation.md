# 修補建議（Remediation Guide）
> 暫時叫 AI 生成的，之後要重寫

本文件說明 `docs/vulnerability-analysis.md` 中七個階段各自的修補方案。這是靶機下架 / 轉為教學範例後，若要把同樣架構用在真實環境時應該採取的修正，**不是**要套用在目前這台故意存在漏洞的 CTF lab 上（套用後靶機就打不通了）。

每一項都區分「根本修補」（fix root cause）與「縱深防禦」（defense in depth，即使根本修補失效也能擋下攻擊）。

---

## Stage 1 — Path Traversal（`materials.py`）

### 根本問題

`filename` 未經驗證即與 `MATERIAL_DIR` 做 `os.path.join`，攻擊者可用 `../` 跳出目錄。

### 修補方案

1. **改用白名單比對，而非黑名單過濾。** 不要嘗試過濾 `../`（容易被 encoding、符號連結等方式繞過），而是把合法檔名維護成一份清單（例如 Stage 1 現有的 `get_materials()` 回傳的四個檔案），請求時只接受清單內的值：

   ```python
   ALLOWED_FILES = {"web_security.pdf", "boyfriend_manual.pdf", "pwn01.pdf", "red_team_intern.pdf"}

   @material_bp.post("/read")
   @require_login
   def read_material():
       filename = request.form.get("file")
       if filename not in ALLOWED_FILES:
           return jsonify({"error": "file not found"}), 404
       path = os.path.join(MATERIAL_DIR, filename)
       return send_file(path)
   ```

2. **若必須支援動態檔名，做路徑正規化 + containment 檢查**，確認解析後的絕對路徑仍在 `MATERIAL_DIR` 之下：

   ```python
   base = os.path.realpath(MATERIAL_DIR)
   target = os.path.realpath(os.path.join(base, filename))
   if os.path.commonpath([base, target]) != base:
       return jsonify({"error": "invalid file"}), 400
   ```

3. **縱深防禦**：以唯讀、最小權限的檔案系統掛載提供靜態教材（例如獨立的 read-only volume 或物件儲存 + 短期簽章 URL），即使應用層被繞過，also 讀不到 `app.py`、`db.py` 等原始碼，因為它們根本不在同一個目錄樹下。

---

## Stage 2 — JSON / JWT Payload Injection（`auth.py`）

### 根本問題

用字串拼接組出要被 `json.loads` 解析的 JSON，未對 `username` 做任何跳脫（escape）。

### 修補方案

1. **永遠用結構化方式建構 JSON，不要手動拼字串。** 直接建立 dict，再交給 `json.dumps` 或直接傳給 `jwt.encode`：

   ```python
   payload = {
       "role": "user",
       "username": username,
       "sub": user_id,
       "iat": int(now.timestamp()),
       "exp": int((now + timedelta(hours=2)).timestamp()),
   }
   token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
   ```

   這樣無論 `username` 內含什麼字元，Python 的 `json` / `PyJWT` 都會做正確的跳脫，不存在「使用者輸入跳出欄位邊界」的問題。

2. **`role` 永遠不該來自任何使用者可控輸入。** 註冊時的 `role` 應該在伺服器端寫死為 `"user"`（用常數，不要用任何拼接或字串運算），權限提升只能透過另一個受保護的管理操作（例如已存在的 admin 幫使用者改權限）完成。

3. **對所有使用者輸入做長度與字元集限制**（例如 `username` 只允許英數字與底線），從輸入層就降低注入面。

4. **縱深防禦**：`require_admin` 不要只信任 JWT 裡的 `role` claim，可在關鍵操作（例如 `/api/admin/*`）額外查一次資料庫裡的即時角色，避免任何簽發時的邏輯錯誤被無限期利用到 token 過期為止。

---

## Stage 3 — SSRF（`webhook.py`）

### 根本問題

`_fetch_url()` 只黑名單擋 `127.0.0.1` / `localhost` 字面值，未限制 scheme，也未檢查 DNS 解析後的實際 IP。

### 修補方案

1. **Scheme allowlist**：只允許 `http` / `https`，直接拒絕 `gopher`、`file`、`ftp` 等：

   ```python
   if parsed.scheme not in ("http", "https"):
       raise ValueError("Unsupported URL scheme")
   ```

2. **對解析後的 IP 做檢查，而不是對 hostname 字串做檢查。** 先 resolve DNS，再檢查目標 IP 是否落在私有網段（RFC1918）、loopback、link-local 等範圍，並鎖定該 IP 送出請求，避免 DNS rebinding：

   ```python
   import ipaddress, socket

   def _is_blocked_ip(ip: str) -> bool:
       addr = ipaddress.ip_address(ip)
       return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved

   resolved_ip = socket.gethostbyname(parsed.hostname)
   if _is_blocked_ip(resolved_ip):
       raise PermissionError("Blocked: internal address")
   ```

3. **內部服務不應該假設「只有可信任的呼叫者」才連得到。** Redis 應該設定 `requirepass`，並用 ACL 限制可執行的指令；即使 SSRF 防護失效，沒有認證的 client 仍無法直接操作。

4. **原則上，需要外部整合（webhook）的功能應該用專屬的 egress proxy / allowlist 網域，而不是讓應用伺服器直接對任意使用者輸入的 URL 發出請求。**

5. **縱深防禦**：`internal_net` 已經是 `internal: true`，這是正確方向；再搭配上述 IP allowlist，即使應用層防護被繞過，網路層仍限制了可達的目的地。

---

## Stage 4 — Celery Pickle 反序列化 RCE（`celery_app.py`）

### 根本問題

`task_serializer` / `result_serializer` / `accept_content` 都設為 `pickle`，pickle 反序列化任意資料等同任意程式碼執行。

### 修補方案

1. **不要用 pickle 作為 message serializer。** 改回 Celery 預設的 `json`：

   ```python
   app.conf.update(
       task_serializer="json",
       result_serializer="json",
       accept_content=["json"],
   )
   ```

2. **原本用 pickle 是因為要傳遞 Matplotlib `Figure` 物件，這個需求應該改成「傳遞可 JSON 序列化的資料，圖片渲染留在 worker 內部完成」**，例如：

   - task 只傳遞產生圖表所需的數值資料（dict / list），由 worker 內部呼叫 Matplotlib 產生圖片，不需要把 `Figure` 物件本身序列化後傳遞。
   - 或者讓 caller 端只傳檔案路徑 / S3 key，worker 讀取後自行產生圖表並寫回去。

3. **如果業務上真的無法避免傳遞複雜 Python 物件，改用有 schema 驗證的序列化格式**（例如自訂 `msgpack` + 明確的欄位驗證，或 `pydantic` model 搭配 JSON），並在 worker 端對收到的欄位做型別與內容檢查，而不是把整個物件圖（object graph）交給反序列化器重建。

4. **Broker 層加上認證與網路隔離。** Redis 作為 broker 應該設定密碼、限制可連線來源，避免任何能碰到 broker 的人都能塞任務進佇列（這是縱深防禦，不解決根本的反序列化問題，但能顯著提高攻擊門檻）。

5. **Worker 進程以最小權限帳號執行**（本專案已用 `celeryuser` 而非 root，這部分設計正確，應保留），限制即使反序列化被觸發，影響範圍也僅限該帳號的權限。

---

## Stage 5 — cron + tar Argument Injection

### 根本問題

root cron 對一個 world-writable 目錄執行 `tar -czf ... *`，shell 展開 `*` 後把攻擊者控制的「檔名」當成 tar 的命令列參數。

### 修補方案

1. **永遠不要對使用者可寫目錄的萬用字元展開結果，直接餵給接受 `-` 開頭參數的指令。** 加上 `--` 明確標示參數結束，之後的內容一律視為檔名，不再解析成選項：

   ```sh
   tar -czf /var/backups/submissions_log.tar.gz -- *
   ```

   這是最小改動且能直接阻斷 `--checkpoint=...` 類型的 argument injection。

2. **更根本的做法：避免 root 對任何非 root 擁有的目錄做萬用字元操作。** 讓這個目錄改由固定清單、程式化列舉（`find ... -print0 | tar --null -T -`）取代 shell glob，並在列舉時排除以 `-` 開頭的異常檔名，或直接拒絕處理。

3. **權限設計上，不該讓 `celeryuser` 對 `/var/log/app` 有寫入權限，卻由 root 排程處理該目錄。** 若該目錄本質上是「不受信任使用者可寫」，root 的自動化工作就不該直接操作它；改由與該目錄同權限等級的帳號（例如同樣是 `celeryuser`）執行備份，或是 root 工作只做唯讀分析、實際壓縮動作交給降權的子程序（例如用 `runuser -u celeryuser` 或直接讓 tar 在降權後的 context 執行）。

4. **縱深防禦**：對排程工作啟用更嚴格的 shell 選項（`set -u`、避免不必要的 glob），並考慮使用 `bsdtar` 等對這類 injection 有額外防護的實作，或在 CI/CD 之外對 cron 內容做定期稽核。

---

## Stage 6 — 憑證明文寫入 Shell History

### 根本問題

`ssh` 指令的密碼直接寫在 `sshpass -p '<password>'` 裡並被記錄進 `.bash_history`，任何取得該帳號 shell（即使只是短暫、非預期）的人都能直接讀到明文密碼。

### 修補方案

1. **不要用密碼做機器對機器（machine-to-machine）的 SSH 認證，改用金鑰。** `opadmin` 應該用 SSH key pair 登入，root 端只保留 private key（權限 `600`），完全不涉及任何密碼字串：

   ```sh
   ssh -i /root/.ssh/id_ed25519 opadmin@ingress
   ```

2. **禁止密碼式 SSH 認證。** 在 `ingress` 的 `sshd_config` 設定：

   ```text
   PasswordAuthentication no
   PubkeyAuthentication yes
   ```

   即使密碼外洩，也無法用來登入。

3. **即使必須用密碼，也不該讓密碼出現在命令列參數或指令字串中。** `sshpass` 支援從檔案（`-f`）或環境變數（`SSHPASS`）讀取密碼，這樣密碼就不會出現在 `.bash_history`、`ps aux`（命令列參數在某些系統上對其他使用者可見）之中：

   ```sh
   SSHPASS="$(cat /run/secrets/ssh_pivot_password)" sshpass -e ssh opadmin@ingress
   ```

   更好的做法是搭配 secret manager（Docker secrets、Vault 等），完全不落地到檔案系統。

4. **關閉不必要的 shell history，或至少不要讓機密操作留下記錄。** 對於自動化腳本（非互動 shell），本來就不該產生 `.bash_history`；若必須手動操作，操作完成後應清除相關記錄，而不是像本靶機刻意保留一份「看起來正常」的歷史紀錄。

5. **憑證輪替。** 任何曾經以明文形式存在過的密碼，一旦暴露風險確認，就應該視為已外洩並立即輪替，不論攻擊者是否已實際取得。

---

## Stage 7 — sudoers Misconfiguration（`NOPASSWD: /usr/bin/vim`）

### 根本問題

允許以 `NOPASSWD` 執行一個功能完整的文字編輯器，而該編輯器本身支援執行外部指令（`:!`），等同直接給予無密碼 root shell。這是 [GTFOBins](https://gtfobins.github.io/) 上典型的 sudo misconfiguration 案例（`vim`、`less`、`awk`、`find` 等具備「執行外部命令」能力的工具都有類似風險）。

### 修補方案

1. **移除這條 sudoers 規則，改用最小權限原則重新設計需求。** 如果 `opadmin` 真的需要用 vim 編輯特定設定檔，不要授權整個 `vim` binary，而是：

   - 用 `sudoedit`（`visudo` 語法中的 `sudoedit /path/to/file`）取代 `sudo vim /path/to/file`。`sudoedit` 會把檔案複製到臨時位置，用**呼叫者自己的**權限開啟編輯器編輯，編輯完再由 sudo 機制搬回原位，過程中呼叫者從未真正以 root 執行 vim 本身，因此無法透過 `:!` 逃逸：

     ```text
     opadmin ALL=(root) NOPASSWD: sudoedit /usr/local/apache2/conf/httpd.conf
     ```

   - 若必須授權，明確限制到特定檔案路徑（不要用萬用字元），且必須搭配 `sudoedit`，不能是可任意執行外部命令的完整編輯器。

2. **禁用有「shell escape」能力的工具透過 sudo 執行。** 在設計任何 `NOPASSWD` 規則前，先查 GTFOBins 確認該工具是否有 `sudo` 條目；有的話一律避免直接授權整個 binary。

3. **必要時用更受限的介面取代通用工具。** 例如需要 reload Apache，就只授權特定指令：

   ```text
   opadmin ALL=(root) NOPASSWD: /usr/local/apache2/bin/httpd -k graceful
   ```

   並確保該指令本身不接受可被利用來執行任意程式的參數（例如自訂 config path 指到攻擊者可寫的檔案）。

4. **稽核所有 sudoers 規則。** 出題或上線前應執行 `sudo -l`（以每個非 root 帳號）逐條檢視，並比對 GTFOBins 清單，任何允許執行完整直譯器 / 編輯器 / 分頁工具的規則都應視為高風險。

5. **縱深防禦**：即使 sudoers 規則暫時無法收緊，也可以搭配 auditd 或類似機制對 `sudo` 的執行做告警，縮短誤用被發現的時間。

---

## 總結：跨關卡的共通原則

| 類別 | 具體做法 |
|---|---|
| 輸入驗證 | 一律用白名單而非黑名單；結構化資料用結構化 API 建構（`json.dumps`、ORM 參數化），不要手動拼字串 |
| 最小權限 | 服務帳號（`celeryuser`）、sudoers 規則、檔案掛載都只給完成任務所需的最小權限 |
| 深度防禦 | 網路層（`internal_net`）、應用層（allowlist）、認證層（Redis `requirepass`、SSH key-only）多層疊加，避免單一防線失效就整條鏈被打穿 |
| 機密管理 | 密碼 / token 不落地到 shell history、命令列參數或原始碼；使用 secret manager 並定期輪替 |
| 序列化安全 | 涉及不可信輸入的反序列化一律避免使用 `pickle` 等會執行任意程式碼的格式，改用 `json` 或有 schema 驗證的格式 |

以上修補若逐一套用到本專案，會讓 Stage 1–7 的攻擊鏈全部失效，可作為靶機退役後轉成「修補前 / 修補後對照」教材的基礎。
