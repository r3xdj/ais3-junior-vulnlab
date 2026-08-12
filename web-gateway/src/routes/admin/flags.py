import os

import redis
from flask import Blueprint, jsonify

from decorators import require_admin


flags_bp = Blueprint("admin_flags", __name__, url_prefix="/api/admin")


def _redis_client():
    return redis.Redis(
        host=os.environ.get("REDIS_HOST", "redis"),
        port=int(os.environ.get("REDIS_PORT", "6379")),
        decode_responses=True,
    )


@flags_bp.get("/flag")
@require_admin
def get_stage2_flag():
    # Stage 3's flag is seeded only after the player has demonstrated
    # administrator access. It is intentionally stored in Redis so that the
    # next step requires the SSRF/gopher primitive rather than another Flask
    # endpoint.
    stage3_flag = os.environ.get("FLAG_STAGE3")
    if stage3_flag:
        _redis_client().set("ctf:flag:stage3", stage3_flag)

    return jsonify({
        "stage": 2,
        "flag": os.environ.get("FLAG_STAGE2", "FLAG_STAGE2_NOT_CONFIGURED"),
    })
