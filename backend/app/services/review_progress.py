import json
from datetime import datetime, timezone
from uuid import uuid4

from redis import Redis

from app.core.config import Settings, get_settings


RELEASE_LOCK_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""


def get_redis_client(settings: Settings | None = None) -> Redis:
    return Redis.from_url(
        (settings or get_settings()).redis_url,
        decode_responses=True,
        socket_connect_timeout=0.5,
        socket_timeout=0.5,
    )


def acquire_review_lock(
    redis_client: Redis,
    *,
    queue_id: int,
    draft_version: int,
    content_hash: str,
    ttl_seconds: int,
) -> str | None:
    token = uuid4().hex
    acquired = redis_client.set(
        review_lock_key(queue_id, draft_version, content_hash),
        token,
        ex=ttl_seconds,
        nx=True,
    )
    return token if acquired else None


def release_review_lock(
    redis_client: Redis,
    *,
    queue_id: int,
    draft_version: int,
    content_hash: str,
    token: str,
) -> None:
    redis_client.eval(
        RELEASE_LOCK_SCRIPT,
        1,
        review_lock_key(queue_id, draft_version, content_hash),
        token,
    )


def write_review_progress(
    redis_client: Redis,
    *,
    queue_id: int,
    draft_version: int,
    status: str,
    ttl_seconds: int,
) -> None:
    payload = {
        "queue_id": queue_id,
        "draft_version": draft_version,
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    redis_client.set(
        review_progress_key(queue_id, draft_version),
        json.dumps(payload, separators=(",", ":")),
        ex=ttl_seconds,
    )


def read_review_progress(
    redis_client: Redis,
    *,
    queue_id: int,
    draft_version: int,
) -> dict | None:
    raw_value = redis_client.get(review_progress_key(queue_id, draft_version))
    if not raw_value:
        return None

    payload = json.loads(raw_value)
    if not isinstance(payload, dict):
        return None
    if payload.get("queue_id") != queue_id or payload.get("draft_version") != draft_version:
        return None
    return payload


def review_lock_key(queue_id: int, draft_version: int, content_hash: str) -> str:
    return f"review:lock:{queue_id}:{draft_version}:{content_hash}"


def review_progress_key(queue_id: int, draft_version: int) -> str:
    return f"review:progress:{queue_id}:{draft_version}"
