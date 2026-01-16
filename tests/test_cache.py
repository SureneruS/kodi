import asyncio

from kodi.cache_backends import InMemoryBackend, NullBackend


class TestNullBackend:
    async def test_get_returns_none(self):
        backend = NullBackend()
        assert await backend.get("any-key") is None

    async def test_set_and_get(self):
        backend = NullBackend()
        await backend.set("key", "value")
        assert await backend.get("key") is None  # always miss

    async def test_delete(self):
        backend = NullBackend()
        await backend.delete("key")  # no-op, should not raise


class TestInMemoryBackend:
    async def test_get_missing_key(self):
        backend = InMemoryBackend()
        assert await backend.get("missing") is None

    async def test_set_and_get(self):
        backend = InMemoryBackend()
        await backend.set("key", "value")
        assert await backend.get("key") == "value"

    async def test_delete(self):
        backend = InMemoryBackend()
        await backend.set("key", "value")
        await backend.delete("key")
        assert await backend.get("key") is None

    async def test_ttl_expiration(self):
        backend = InMemoryBackend()
        await backend.set("key", "value", ttl=1)
        assert await backend.get("key") == "value"
        await asyncio.sleep(1.1)
        assert await backend.get("key") is None

    async def test_close_clears_store(self):
        backend = InMemoryBackend()
        await backend.set("key", "value")
        await backend.close()
        assert await backend.get("key") is None
