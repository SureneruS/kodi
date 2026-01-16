import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import kodi
from kodi.exceptions import KodiContextNotLoadedError, KodiNotInitializedError
from kodi.models import Flag, TenantFlag, UserFlag


async def create_flag(session: AsyncSession, name: str, enabled: bool = False) -> Flag:
    flag = Flag(name=name, enabled=enabled)
    session.add(flag)
    await session.commit()
    await session.refresh(flag)
    return flag


async def create_tenant_override(
    session: AsyncSession, flag: Flag, tenant_id: str, enabled: bool
) -> TenantFlag:
    override = TenantFlag(flag_id=flag.id, tenant_id=tenant_id, enabled=enabled)
    session.add(override)
    await session.commit()
    return override


async def create_user_override(
    session: AsyncSession, flag: Flag, tenant_id: str, user_id: str, enabled: bool
) -> UserFlag:
    override = UserFlag(flag_id=flag.id, tenant_id=tenant_id, user_id=user_id, enabled=enabled)
    session.add(override)
    await session.commit()
    return override


class TestInit:
    async def test_not_initialized_raises_error(self):
        with pytest.raises(KodiNotInitializedError):
            await kodi.load_context()

    async def test_init_creates_tables(self, engine):
        await kodi.init(engine=engine, cache=None)
        async with engine.connect() as conn:
            result = await conn.execute(select(Flag))
            assert result.fetchall() == []
        await kodi.close()


class TestLoadContext:
    async def test_context_not_loaded_raises_error(self, initialized_kodi):
        with pytest.raises(KodiContextNotLoadedError):
            kodi.is_enabled("any-flag")

    async def test_load_context_enables_sync_checks(self, initialized_kodi):
        await kodi.load_context()
        assert kodi.is_enabled("nonexistent") is False


class TestFlagEvaluation:
    async def test_unknown_flag_returns_false(self, initialized_kodi):
        await kodi.load_context()
        assert kodi.is_enabled("unknown-flag") is False

    async def test_platform_flag_enabled(self, initialized_kodi, engine):
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            await create_flag(session, "test-flag", enabled=True)

        await kodi.load_context()
        assert kodi.is_enabled("test-flag") is True

    async def test_platform_flag_disabled(self, initialized_kodi, engine):
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            await create_flag(session, "test-flag", enabled=False)

        await kodi.load_context()
        assert kodi.is_enabled("test-flag") is False

    async def test_tenant_override_wins_over_platform(self, initialized_kodi, engine):
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            flag = await create_flag(session, "test-flag", enabled=False)
            await create_tenant_override(session, flag, "tenant-1", enabled=True)

        await kodi.load_context(tenant_id="tenant-1")
        assert kodi.is_enabled("test-flag") is True

    async def test_user_override_wins_over_tenant(self, initialized_kodi, engine):
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            flag = await create_flag(session, "test-flag", enabled=False)
            await create_tenant_override(session, flag, "tenant-1", enabled=True)
            await create_user_override(session, flag, "tenant-1", "user-1", enabled=False)

        await kodi.load_context(tenant_id="tenant-1", user_id="user-1")
        assert kodi.is_enabled("test-flag") is False

    async def test_user_override_wins_over_platform(self, initialized_kodi, engine):
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            flag = await create_flag(session, "test-flag", enabled=True)
            await create_user_override(session, flag, "tenant-1", "user-1", enabled=False)

        await kodi.load_context(tenant_id="tenant-1", user_id="user-1")
        assert kodi.is_enabled("test-flag") is False


class TestConvenienceFunctions:
    async def test_is_disabled(self, initialized_kodi, engine):
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            await create_flag(session, "disabled-flag", enabled=False)
            await create_flag(session, "enabled-flag", enabled=True)

        await kodi.load_context()
        assert kodi.is_disabled("disabled-flag") is True
        assert kodi.is_disabled("enabled-flag") is False

    async def test_get_all(self, initialized_kodi, engine):
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            await create_flag(session, "flag-a", enabled=True)
            await create_flag(session, "flag-b", enabled=False)

        await kodi.load_context()
        all_flags = kodi.get_all()
        assert all_flags == {"flag-a": True, "flag-b": False}

    async def test_get_enabled(self, initialized_kodi, engine):
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            await create_flag(session, "flag-a", enabled=True)
            await create_flag(session, "flag-b", enabled=False)
            await create_flag(session, "flag-c", enabled=True)

        await kodi.load_context()
        enabled = kodi.get_enabled()
        assert set(enabled) == {"flag-a", "flag-c"}

    async def test_is_any_enabled(self, initialized_kodi, engine):
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            await create_flag(session, "flag-a", enabled=False)
            await create_flag(session, "flag-b", enabled=True)

        await kodi.load_context()
        assert kodi.is_any_enabled("flag-a", "flag-b") is True
        assert kodi.is_any_enabled("flag-a", "nonexistent") is False

    async def test_is_all_enabled(self, initialized_kodi, engine):
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            await create_flag(session, "flag-a", enabled=True)
            await create_flag(session, "flag-b", enabled=True)
            await create_flag(session, "flag-c", enabled=False)

        await kodi.load_context()
        assert kodi.is_all_enabled("flag-a", "flag-b") is True
        assert kodi.is_all_enabled("flag-a", "flag-c") is False


class TestOverride:
    async def test_override_context_manager(self, initialized_kodi, engine):
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            await create_flag(session, "test-flag", enabled=False)

        await kodi.load_context()
        assert kodi.is_enabled("test-flag") is False

        with kodi.override({"test-flag": True}):
            assert kodi.is_enabled("test-flag") is True

        assert kodi.is_enabled("test-flag") is False

    async def test_override_with_new_flag(self, initialized_kodi):
        await kodi.load_context()

        with kodi.override({"new-flag": True}):
            assert kodi.is_enabled("new-flag") is True


class TestAsyncCheck:
    async def test_is_enabled_async(self, initialized_kodi, engine):
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            flag = await create_flag(session, "test-flag", enabled=False)
            await create_tenant_override(session, flag, "tenant-1", enabled=True)

        result = await kodi.is_enabled_async("test-flag", tenant_id="tenant-1")
        assert result is True

        result = await kodi.is_enabled_async("test-flag", tenant_id="tenant-2")
        assert result is False
