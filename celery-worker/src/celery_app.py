import os
from celery import Celery

redis_host = os.environ.get('REDIS_HOST', 'redis')
redis_port = os.environ.get('REDIS_PORT', '6379')
broker_url = f'redis://{redis_host}:{redis_port}/0'

app = Celery('ais3_tasks', broker=broker_url, backend=broker_url, include=['tasks'])

app.conf.update(
    task_serializer='pickle',
    result_serializer='pickle',
    accept_content=['pickle'],
    # ----------------------------------------

    task_routes={
        'tasks.generate_certificate': {'queue': 'celery'},
    }
)