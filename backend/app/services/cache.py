# app/services/cache.py
# Cache-aside with Redis:
#   1. read the cache  2. on a miss, compute from PostgreSQL  3. store it with a TTL.
# On every new attempt we delete the dashboard keys, so tutors never wait
# a full TTL to see fresh numbers.
# If REDIS_URL is empty or Redis is down, every call quietly does nothing,
# so the app still works (just slower).

import json
import logging

import redis

from ..config import settings

log = logging.getLogger(__name__)

DASHBOARD_KEYS = ["dashboard:stats", "dashboard:concepts"]

_redis = (
    redis.Redis.from_url(settings.redis_url, decode_responses=True,
                         socket_connect_timeout=1, socket_timeout=1)
    if settings.redis_url else None
)


def cache_get(key: str):
    if _redis is None:
        return None
    try:
        raw = _redis.get(key)
        return json.loads(raw) if raw else None
    except redis.RedisError as exc:
        log.warning("cache get failed: %s", exc)
        return None


def cache_set(key: str, value, ttl: int | None = None) -> None:
    if _redis is None:
        return
    try:
        _redis.set(key, json.dumps(value), ex=ttl or settings.cache_ttl_seconds)
    except redis.RedisError as exc:
        log.warning("cache set failed: %s", exc)


def cache_delete(*keys: str) -> None:
    if _redis is None or not keys:
        return
    try:
        _redis.delete(*keys)
    except redis.RedisError as exc:
        log.warning("cache delete failed: %s", exc)


def redis_ok() -> bool:
    """Used by /health."""
    if _redis is None:
        return False
    try:
        return bool(_redis.ping())
    except redis.RedisError:
        return False
