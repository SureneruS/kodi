import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

import kodi
from kodi.models import Base


@pytest.fixture
async def engine() -> AsyncEngine:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def initialized_kodi(engine: AsyncEngine):
    await kodi.init(engine=engine, cache=None)
    yield
    await kodi.close()
