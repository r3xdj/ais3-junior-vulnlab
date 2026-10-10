from celery import Celery

app = Celery(
    "demo",
    broker="redis://localhost:6379/0",
)

app.conf.update(
    task_serializer='pickle',
    accept_content=['pickle'],
    task_default_queue='celery',
)

@app.task(bind=True)
def test(self):
    return 0