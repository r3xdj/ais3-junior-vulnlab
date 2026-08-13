from celery import Celery
import pprint

app = Celery(
    "demo",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)

@app.task(bind=True)
def add(self, x, y):
    print("\n=== REQUEST ===")
    for key, value in self.request.__dict__.items():
        print(f"{key}: {value}")
    return x + y