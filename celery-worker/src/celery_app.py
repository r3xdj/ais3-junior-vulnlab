import os
from celery import Celery

redis_host = os.environ.get('REDIS_HOST', 'redis')
redis_port = os.environ.get('REDIS_PORT', '6379')
broker_url = f'redis://{redis_host}:{redis_port}/0'

app = Celery('ais3_tasks', broker=broker_url, backend=broker_url, include=['tasks'])

app.conf.update(
    # --- Stage 4 漏洞設計:啟用 pickle 序列化 ---
    # 業務理由:結業證書任務需要傳遞 Matplotlib Figure 物件(無法 JSON 序列化)
    # 漏洞後果:攻擊者可向 Redis 佇列注入惡意 Pickle payload,
    #           Worker 取出時反序列化觸發任意程式碼執行
    task_serializer='pickle',
    result_serializer='pickle',
    accept_content=['pickle'],
    # ----------------------------------------

    task_routes={
        'tasks.generate_certificate': {'queue': 'celery'},
    }
)