from kodi.cache import CacheBackend
from kodi.cache_backends import InMemoryBackend, NullBackend, RedisBackend
from kodi.core import (
    close,
    get_all,
    get_enabled,
    init,
    invalidate_cache,
    is_all_enabled,
    is_any_enabled,
    is_disabled,
    is_enabled,
    is_enabled_async,
    load_context,
    override,
)
from kodi.exceptions import KodiContextNotLoadedError, KodiError, KodiNotInitializedError
from kodi.models import Flag, TenantFlag, UserFlag

__version__ = "0.1.0"

__all__ = [
    # Core API
    "init",
    "close",
    "load_context",
    "is_enabled",
    "is_disabled",
    "get_all",
    "get_enabled",
    "is_any_enabled",
    "is_all_enabled",
    "is_enabled_async",
    "override",
    "invalidate_cache",
    # Cache
    "CacheBackend",
    "RedisBackend",
    "InMemoryBackend",
    "NullBackend",
    # Models
    "Flag",
    "TenantFlag",
    "UserFlag",
    # Exceptions
    "KodiError",
    "KodiNotInitializedError",
    "KodiContextNotLoadedError",
]
