import json
from contextlib import contextmanager

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from kodi.cache import CacheBackend, CacheKeys
from kodi.cache_backends import NullBackend, create_redis_backend
from kodi.context import FlagContext, clear_context, get_context, set_context
from kodi.exceptions import (
    KodiContextNotLoadedError,
    KodiNotInitializedError,
    warn_unknown_flag,
)
from kodi.models import Flag, TenantFlag, UserFlag
from kodi.schema import init_schema


class _State:
    engine: AsyncEngine | None = None
    session_factory: async_sessionmaker[AsyncSession] | None = None
    cache: CacheBackend | None = None


_state = _State()


async def init(
    engine: AsyncEngine,
    cache: str | CacheBackend | None = None,
) -> None:
    """Initialize kodi with database engine and optional cache."""
    _state.engine = engine
    _state.session_factory = async_sessionmaker(engine, expire_on_commit=False)

    if cache is None:
        _state.cache = NullBackend()
    elif isinstance(cache, str):
        _state.cache = await create_redis_backend(cache)
    else:
        _state.cache = cache

    await init_schema(engine)


async def close() -> None:
    """Clean up resources."""
    if _state.cache:
        await _state.cache.close()
    _state.engine = None
    _state.session_factory = None
    _state.cache = None


def _check_initialized() -> None:
    if _state.session_factory is None:
        raise KodiNotInitializedError()


def _check_context() -> FlagContext:
    ctx = get_context()
    if ctx is None:
        raise KodiContextNotLoadedError()
    return ctx


async def load_context(
    tenant_id: str | None = None,
    user_id: str | None = None,
) -> None:
    """Load flag states for the given tenant/user into context."""
    _check_initialized()

    flags = await _fetch_flags(tenant_id, user_id)
    ctx = FlagContext(tenant_id=tenant_id, user_id=user_id, flags=flags)
    set_context(ctx)


async def _fetch_flags(
    tenant_id: str | None,
    user_id: str | None,
) -> dict[str, bool]:
    """Fetch all flags and resolve values for the given context."""
    assert _state.session_factory is not None
    assert _state.cache is not None

    platform_flags = await _get_cached_flags()
    tenant_overrides = await _get_cached_tenant_overrides(tenant_id) if tenant_id else {}
    user_overrides = (
        await _get_cached_user_overrides(tenant_id, user_id)
        if tenant_id and user_id
        else {}
    )

    result: dict[str, bool] = {}
    for name, enabled in platform_flags.items():
        if name in user_overrides:
            result[name] = user_overrides[name]
        elif name in tenant_overrides:
            result[name] = tenant_overrides[name]
        else:
            result[name] = enabled

    return result


async def _get_cached_flags() -> dict[str, bool]:
    assert _state.cache is not None
    assert _state.session_factory is not None

    cached = await _state.cache.get(CacheKeys.flags())
    if cached:
        return json.loads(cached)

    async with _state.session_factory() as session:
        result = await session.execute(select(Flag.name, Flag.enabled))
        flags = {row.name: row.enabled for row in result}

    await _state.cache.set(CacheKeys.flags(), json.dumps(flags))
    return flags


async def _get_cached_tenant_overrides(tenant_id: str) -> dict[str, bool]:
    assert _state.cache is not None
    assert _state.session_factory is not None

    cached = await _state.cache.get(CacheKeys.tenant(tenant_id))
    if cached:
        return json.loads(cached)

    async with _state.session_factory() as session:
        result = await session.execute(
            select(Flag.name, TenantFlag.enabled)
            .join(TenantFlag, Flag.id == TenantFlag.flag_id)
            .where(TenantFlag.tenant_id == tenant_id)
        )
        overrides = {row.name: row.enabled for row in result}

    await _state.cache.set(CacheKeys.tenant(tenant_id), json.dumps(overrides))
    return overrides


async def _get_cached_user_overrides(tenant_id: str, user_id: str) -> dict[str, bool]:
    assert _state.cache is not None
    assert _state.session_factory is not None

    cached = await _state.cache.get(CacheKeys.user(tenant_id, user_id))
    if cached:
        return json.loads(cached)

    async with _state.session_factory() as session:
        result = await session.execute(
            select(Flag.name, UserFlag.enabled)
            .join(UserFlag, Flag.id == UserFlag.flag_id)
            .where(UserFlag.tenant_id == tenant_id, UserFlag.user_id == user_id)
        )
        overrides = {row.name: row.enabled for row in result}

    await _state.cache.set(CacheKeys.user(tenant_id, user_id), json.dumps(overrides))
    return overrides


def is_enabled(name: str) -> bool:
    """Check if a flag is enabled. Requires load_context() to be called first."""
    ctx = _check_context()
    if name not in ctx.flags:
        warn_unknown_flag(name)
        return False
    return ctx.flags[name]


def is_disabled(name: str) -> bool:
    """Check if a flag is disabled. Requires load_context() to be called first."""
    return not is_enabled(name)


def get_all() -> dict[str, bool]:
    """Get all flag states. Requires load_context() to be called first."""
    ctx = _check_context()
    return dict(ctx.flags)


def get_enabled() -> list[str]:
    """Get list of enabled flag names. Requires load_context() to be called first."""
    ctx = _check_context()
    return [name for name, enabled in ctx.flags.items() if enabled]


def is_any_enabled(*names: str) -> bool:
    """Check if any of the given flags are enabled."""
    ctx = _check_context()
    for name in names:
        if name not in ctx.flags:
            warn_unknown_flag(name)
            continue
        if ctx.flags[name]:
            return True
    return False


def is_all_enabled(*names: str) -> bool:
    """Check if all of the given flags are enabled."""
    ctx = _check_context()
    for name in names:
        if name not in ctx.flags:
            warn_unknown_flag(name)
            return False
        if not ctx.flags[name]:
            return False
    return True


async def is_enabled_async(
    name: str,
    tenant_id: str | None = None,
    user_id: str | None = None,
) -> bool:
    """Check if a flag is enabled without requiring load_context()."""
    _check_initialized()
    flags = await _fetch_flags(tenant_id, user_id)
    if name not in flags:
        warn_unknown_flag(name)
        return False
    return flags[name]


@contextmanager
def override(flags: dict[str, bool]):
    """Context manager to override flag values for testing."""
    prev_ctx = get_context()
    prev_flags = prev_ctx.flags if prev_ctx else {}

    new_flags = {**prev_flags, **flags}
    new_ctx = FlagContext(
        tenant_id=prev_ctx.tenant_id if prev_ctx else None,
        user_id=prev_ctx.user_id if prev_ctx else None,
        flags=new_flags,
    )
    set_context(new_ctx)
    try:
        yield
    finally:
        if prev_ctx:
            set_context(prev_ctx)
        else:
            clear_context()


async def invalidate_cache(
    scope: str, tenant_id: str | None = None, user_id: str | None = None
) -> None:
    """Invalidate cache for the given scope. Called by admin on writes."""
    if _state.cache is None:
        return

    if scope == "flags":
        await _state.cache.delete(CacheKeys.flags())
    elif scope == "tenant" and tenant_id:
        await _state.cache.delete(CacheKeys.tenant(tenant_id))
    elif scope == "user" and tenant_id and user_id:
        await _state.cache.delete(CacheKeys.user(tenant_id, user_id))
