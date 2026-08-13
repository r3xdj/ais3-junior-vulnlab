# Celery Lab

## Build

```bash
docker build -t celery-lab .
```

## Start

```bash
docker run --rm -it --name celery-lab celery-lab
```

## Check

```bash
docker exec -it celery-lab redis-cli MONITOR
```

```bash
docker exec -it celery-lab python -c "from tasks import add; add.delay(3,4)"
```

```bash
docker exec -it celery-lab python decode_task.py
```
