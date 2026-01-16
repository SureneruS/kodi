from typing import Protocol, runtime_checkable


@runtime_checkable
class CacheBackend(Protocol):
    async def get(self, key: str) -> str | None:
        """Get value by key, return None if not found."""
        ...

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        """Set value with optional TTL in seconds."""
        ...

    async def delete(self, key: str) -> None:
        """Delete key."""
        ...

    async def close(self) -> None:
        """Clean up resources."""
        ...


class CacheKeys:
    PREFIX = "kodi"

    @classmethod
    def flags(cls) -> str:
        return f"{cls.PREFIX}:flags"

    @classmethod
    def tenant(cls, tenant_id: str) -> str:
        return f"{cls.PREFIX}:tenant:{tenant_id}"

    @classmethod
    def user(cls, tenant_id: str, user_id: str) -> str:
        return f"{cls.PREFIX}:user:{tenant_id}:{user_id}"
