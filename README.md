# Kodi

Simple, robust feature flags for Python applications.

## Features

- Simple on/off toggles with multi-level overrides (platform → tenant → user)
- Works with any SQLAlchemy-supported database
- Optional Redis caching with automatic invalidation
- FastAPI integration (middleware + evaluate endpoint)
- sqladmin integration for flag management UI
- Sync flag checks after context is loaded
- Testing utilities for easy flag overrides

## Installation

```bash
pip install kodi                 # Core only
pip install kodi[redis]          # With Redis caching
pip install kodi[fastapi]        # With FastAPI router
pip install kodi[admin]          # With sqladmin views
pip install kodi[all]            # Everything
```

## Quick Start

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine
import kodi

engine = create_async_engine("postgresql+asyncpg://...")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await kodi.init(engine=engine, cache="redis://localhost:6379/0")
    yield
    await kodi.close()

app = FastAPI(lifespan=lifespan)

@app.middleware("http")
async def feature_flags_middleware(request, call_next):
    await kodi.load_context(
        tenant_id=request.state.tenant_id,
        user_id=request.state.user_id,
    )
    return await call_next(request)

@app.get("/dashboard")
async def dashboard():
    if kodi.is_enabled("new-dashboard"):
        return {"version": "new"}
    return {"version": "old"}
```

## API

### Initialization

```python
await kodi.init(
    engine=engine,                      # SQLAlchemy AsyncEngine (required)
    cache="redis://localhost:6379/0",   # Redis URL, or
    cache=RedisBackend(client),         # Redis client, or
    cache=InMemoryBackend(),            # In-memory cache, or
    cache=None,                         # No caching
)
```

### Loading Context

```python
await kodi.load_context(tenant_id="acme", user_id="user123")
```

### Flag Checks

```python
kodi.is_enabled("feature")          # True/False
kodi.is_disabled("feature")         # Inverse
kodi.get_all()                      # {"feature": True, ...}
kodi.get_enabled()                  # ["feature", ...]
kodi.is_any_enabled("a", "b")       # OR
kodi.is_all_enabled("a", "b")       # AND
```

### Async Check (without middleware)

```python
await kodi.is_enabled_async("feature", tenant_id="t1", user_id="u1")
```

### Testing

```python
with kodi.override({"feature": True}):
    assert kodi.is_enabled("feature")
```

## Flag Hierarchy

Most specific wins:
1. User override (if set) → returned
2. Tenant override (if set) → returned
3. Platform default → returned
4. Flag not found → False + warning log

## License

MIT
