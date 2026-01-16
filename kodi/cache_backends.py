from time import time
from typing import Any


class NullBackend:
    """No-op cache backend. Always returns cache miss."""

    async def get(self, key: str) -> str | None:
        return None

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        pass

    async def delete(self, key: str) -> None:
        pass

    async def close(self) -> None:
        pass


class InMemoryBackend:
    """Simple dict-based cache. Only works within a single process."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float | None]] = {}

    async def get(self, key: str) -> str | None:
        if key not in self._store:
            return None
        value, expires_at = self._store[key]
        if expires_at is not None and time() > expires_at:
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        expires_at = time() + ttl if ttl else None
        self._store[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def close(self) -> None:
        self._store.clear()


class RedisBackend:
    """Redis cache backend."""

    def __init__(self, client: Any) -> None:
        self._client = client

    async def get(self, key: str) -> str | None:
        value = await self._client.get(key)
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        if ttl:
            await self._client.set(key, value, ex=ttl)
        else:
            await self._client.set(key, value)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def close(self) -> None:
        await self._client.aclose()


async def create_redis_backend(url: str) -> RedisBackend:
    """Create a RedisBackend from a URL."""
    try:
        from redis.asyncio import from_url
    except ImportError:
        raise ImportError("redis package required. Install with: pip install kodi[redis]")

    client = from_url(url)
    return RedisBackend(client)
