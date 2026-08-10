from flask import Blueprint, request, jsonify
from decorators import require_admin
import pycurl
import urllib.parse
from io import BytesIO

webhook_bp = Blueprint('webhook', __name__, url_prefix='/api/admin')

@webhook_bp.route('/webhook-test', methods=['POST'])
@require_admin
def webhook_test():
    """
    模擬「助教 Discord/Slack 課程公告 Bot 連線測試」功能。
    業務理由:團隊採用 pycurl 而非 requests,是因為需要更細緻的
    connection timeout 控制、以及未來可能串接的內部訊息佇列服務。

    漏洞成因(真實世界常見錯誤):
    - 只用簡單黑名單擋掉 127.0.0.1 / localhost,忘記限制 hostname 為 service name 的情況
    - 沒有呼叫 CURLOPT_PROTOCOLS 限制協定白名單,libcurl 預設支援
      http/https/ftp/gopher/dict/file 等一大票協定
    - gopher:// 協定可以送任意 raw bytes 到指定 host:port,
      因此能拿來跟 Redis 這類純文字協定的服務直接對話
    """
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"error": "Missing url field"}), 400

    target_url = data['url']
    parsed = urllib.parse.urlparse(target_url)

    # 半防護:只擋最明顯的 loopback,沒擋 service name,也沒限制協定範圍
    if not parsed.scheme or not parsed.hostname: return jsonify({"error": "Invalid URL format"}), 400

    if parsed.hostname in ('127.0.0.1', 'localhost'):
        return jsonify({"error": "Blocked: cannot connect to loopback address"}), 403

    buffer = BytesIO()
    c = pycurl.Curl()
    try:
        c.setopt(pycurl.URL, target_url)
        c.setopt(pycurl.WRITEDATA, buffer)
        c.setopt(pycurl.TIMEOUT, 5)
        c.setopt(pycurl.POST, 1)
        c.setopt(pycurl.POSTFIELDS, '{"text": "AIS3 Bot connection test"}')
        # 注意:這裡沒有設定 c.setopt(pycurl.PROTOCOLS, pycurl.PROTO_HTTP | pycurl.PROTO_HTTPS)
        # 因此 libcurl 允許使用任何它支援的協定,包含 gopher
        c.perform()
        status = c.getinfo(pycurl.RESPONSE_CODE)
        body = buffer.getvalue().decode('utf-8', errors='replace')
        return jsonify({"status": status, "body": body})
    except pycurl.error as e:
        args = e.args
        if len(args) == 2:
            errno, errstr = args
        else:
            errno = None
            errstr = args[0] if args else ''
        partial = buffer.getvalue()
        # errno 28 = CURLE_OPERATION_TIMEDOUT
        # gopher/raw TCP 服務(如 Redis)通常不會主動關閉連線,
        # 逾時前收到的資料仍然有效,不當作失敗處理
        if errno == 28 and partial:
            return jsonify({
                "status": "partial_response_on_timeout",
                "body": partial.decode('utf-8', errors='replace')
            })
        return jsonify({"error": errstr}), 502
    finally:
        c.close()