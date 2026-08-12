import os

from celery import Celery

import db


def _celery_client():
    broker = f"redis://{os.environ.get('REDIS_HOST', 'redis')}:{os.environ.get('REDIS_PORT', '6379')}/0"
    celery = Celery('certificate_dispatch', broker=broker)
    celery.conf.update(
        task_serializer='pickle',
        result_serializer='pickle',
        accept_content=['pickle'],
        task_default_queue='celery',
    )
    return celery


def queue_certificate_generation(certificate: dict, user: dict):
    """Queue a certificate build using the user's current profile data."""
    scores = certificate['scores']
    payload = {
        'certificate_id': certificate['id'],
        'user_id': user['id'],
        'name': user.get('display_name') or user['username'],
        'username': user['username'],
        'email': user.get('email'),
        'scores': scores,
        'average_score': certificate['average_score'],
        'grade': certificate['grade'],
        'course': 'AIS3 Junior 2026',
    }
    _celery_client().send_task('tasks.generate_certificate', args=[payload])


def regenerate_existing_certificate(user_id: int):
    """Mark an existing certificate pending and queue a fresh PDF."""
    certificate = db.get_certificate_by_user_id(user_id)
    if not certificate:
        return False

    db.mark_certificate_pending(certificate['id'])
    certificate = db.get_certificate_by_user_id(user_id)
    user = db.get_user_by_id(user_id)
    queue_certificate_generation(certificate, user)
    return True
