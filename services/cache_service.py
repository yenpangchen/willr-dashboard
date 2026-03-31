from __future__ import annotations

import json
import logging
from typing import Any

from redis import Redis

from config.settings import settings

logger = logging.getLogger(__name__)
_redis_client: Redis | None = None
_redis_failed = False


def _redis() -> Redis | None:
    global _redis_client, _redis_failed
    if not settings.cache_enabled or _redis_failed:
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        client = Redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=0.7)
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception:
        _redis_failed = True
        logger.warning("redis_unavailable")
        return None


def build_snapshot_cache_key(period: int, sort_key: str, recent: int) -> str:
    return f"{settings.cache_key_prefix}:snapshot:tw50:p{period}:s{sort_key}:r{recent}"


def get_json(key: str) -> dict[str, Any] | None:
    client = _redis()
    if client is None:
        return None
    try:
        raw = client.get(key)
        if not raw:
            return None
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def set_json(key: str, payload: dict[str, Any], ttl_seconds: int) -> None:
    client = _redis()
    if client is None:
        return
    try:
        client.setex(key, max(1, ttl_seconds), json.dumps(payload, ensure_ascii=True))
    except Exception:
        return


def invalidate_snapshot_cache() -> int:
    client = _redis()
    if client is None:
        return 0
    deleted = 0
    pattern = f"{settings.cache_key_prefix}:snapshot:*"
    try:
        for k in client.scan_iter(match=pattern, count=200):
            deleted += int(client.delete(k))
    except Exception:
        return deleted
    return deleted
