import redis
import json
import base64
import pprint

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

raw = r.lindex("celery", 0)

if raw is None:
    print("No task found in Redis.")
    exit()

envelope = json.loads(raw)

print("=== ENVELOPE ===")
pprint.pp(envelope, sort_dicts=False)

print("\n=== BODY ===")
body = base64.b64decode(envelope["body"])
pprint.pp(json.loads(body), sort_dicts=False)