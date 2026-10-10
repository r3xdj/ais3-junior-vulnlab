import redis
import json
import pprint

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

raw = r.lindex("celery", 0)

if raw is None:
    print("No task found in Redis.")
    print("Please run:")
    print("""\tdocker exec -it celery-lab python -c "from tasks import test; test.delay()" """)
    print("To enqueue a task first.")
          
    exit()

envelope = json.loads(raw)

pprint.pp(envelope, sort_dicts=False)