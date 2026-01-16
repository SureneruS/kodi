from sqlalchemy import inspect, select, text
from sqlalchemy.ext.asyncio import AsyncEngine

from kodi.models import Base, SchemaVersion

CURRENT_VERSION = 1


async def init_schema(engine: AsyncEngine) -> None:
    """Initialize or upgrade the database schema."""
    async with engine.begin() as conn:
        # Check if tables exist
        def check_tables(sync_conn):  # type: ignore
            inspector = inspect(sync_conn)
            return inspector.has_table("kodi_schema_version")

        has_schema = await conn.run_sync(check_tables)

        if not has_schema:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(
                text("INSERT INTO kodi_schema_version (id, version) VALUES (1, :version)"),
                {"version": CURRENT_VERSION},
            )
            return

        result = await conn.execute(select(SchemaVersion.version))
        row = result.scalar_one_or_none()
        current = row if row else 0

        if current < CURRENT_VERSION:
            await _run_upgrades(conn, current)


async def _run_upgrades(conn, from_version: int) -> None:  # type: ignore
    """Run schema upgrades from from_version to CURRENT_VERSION."""
    for version in range(from_version + 1, CURRENT_VERSION + 1):
        upgrade_func = _UPGRADES.get(version)
        if upgrade_func:
            await upgrade_func(conn)

    await conn.execute(
        text("UPDATE kodi_schema_version SET version = :version WHERE id = 1"),
        {"version": CURRENT_VERSION},
    )


_UPGRADES: dict = {
    # Example: 2: _upgrade_to_v2,
}
