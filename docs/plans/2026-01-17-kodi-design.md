# Kodi - Feature Flags Library Design

## Overview

Kodi is a simple, robust feature flags library for Python applications. It supports multi-tenant applications with user-level overrides, PostgreSQL (or any SQLAlchemy-supported database) as the data store, optional Redis caching, and integrates with FastAPI and sqladmin.

## Core Decisions

| Aspect | Decision |
|--------|----------|
| **Name** | kodi (Tamil for "flag") |
| **Flag model** | Simple toggles (on/off) |
| **Hierarchy** | Most specific wins (user > tenant > platform) |
| **Admin UI** | sqladmin |
| **Cache** | Generic protocol; Redis, in-memory, or custom backends |
| **Distribution** | Public PyPI |
| **IDs** | String-based (tenant_id, user_id) |
| **DB** | Any SQLAlchemy-supported database |
| **Context** | Middleware loads, sync checks; or explicit async checks |
| **Unknown flags** | Return False + warning log |
| **Schema** | Idempotent init with version upgrades |
| **REST API** | Evaluate endpoint only; management via sqladmin |
| **Auth** | App provides auth dependency |

## Data Model

### Tables

```
kodi_schema_version
  - version: int (current schema version)

kodi_flags (platform-level flags)
  - id: str (primary key, auto-generated)
  - name: str (unique, e.g., "dark-mode")
  - description: str (optional)
  - enabled: bool (platform default)
  - created_at: datetime
  - updated_at: datetime

kodi_tenant_flags (tenant overrides)
  - id: str (primary key)
  - flag_id: str (FK to kodi_flags)
  - tenant_id: str (from app)
  - enabled: bool
  - created_at: datetime
  - updated_at: datetime
  - unique(flag_id, tenant_id)

kodi_user_flags (user overrides)
  - id: str (primary key)
  - flag_id: str (FK to kodi_flags)
  - tenant_id: str (from app)
  - user_id: str (from app)
  - enabled: bool
  - created_at: datetime
  - updated_at: datetime
  - unique(flag_id, tenant_id, user_id)
```

### Evaluation Logic (most specific wins)

1. Check `kodi_user_flags` for (flag, tenant, user) → if found, return that value
2. Check `kodi_tenant_flags` for (flag, tenant) → if found, return that value
3. Check `kodi_flags` for flag → if found, return platform default
4. Flag not found → log warning, return False

## Public API

### Initialization

```python
import kodi

await kodi.init(
    engine=your_async_engine,           # SQLAlchemy AsyncEngine
    cache="redis://localhost:6379/0",   # URL string, or
    # cache=RedisBackend(your_client),  # existing client, or
    # cache=InMemoryBackend(),          # in-memory, or
    # cache=None,                       # no cache
)
```

### Middleware (recommended)

```python
@app.middleware("http")
async def feature_flags_middleware(request: Request, call_next):
    tenant_id = get_tenant_id(request)  # app-specific
    user_id = get_user_id(request)      # app-specific

    await kodi.load_context(tenant_id=tenant_id, user_id=user_id)
    return await call_next(request)
```

### Flag Checks

```python
# Sync checks (after load_context)
kodi.is_enabled("dark-mode")
kodi.is_disabled("legacy-feature")

# Get all flags
kodi.get_all()        # → {"dark-mode": True, "new-checkout": False}
kodi.get_enabled()    # → ["dark-mode", "beta-feature"]

# Bulk checks
kodi.is_any_enabled("promo-a", "promo-b")  # OR
kodi.is_all_enabled("part-1", "part-2")    # AND

# Async check (without middleware)
await kodi.is_enabled_async("flag", tenant_id="t1", user_id="u1")
```

### Testing

```python
with kodi.override({"new-checkout": True, "dark-mode": False}):
    result = await checkout_flow()
    assert result.uses_new_flow
```

### Cleanup

```python
await kodi.close()
```

## Cache Architecture

### Protocol

```python
class CacheBackend(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str, ttl: int | None = None) -> None: ...
    async def delete(self, key: str) -> None: ...
```

### Built-in Backends

- `RedisBackend` - Redis client wrapper
- `InMemoryBackend` - Dict-based (single instance)
- `NullBackend` - No-op (always cache miss)

### Cache Keys

```
kodi:flags                          → all platform flags
kodi:tenant:{tenant_id}             → tenant overrides
kodi:user:{tenant_id}:{user_id}     → user overrides
```

### Invalidation

On write (via sqladmin), delete relevant cache keys. Next read fetches fresh data.

## sqladmin Integration

```python
from sqladmin import Admin
from kodi.admin import FlagAdmin, TenantFlagAdmin, UserFlagAdmin

admin = Admin(app, engine)
admin.add_view(FlagAdmin)
admin.add_view(TenantFlagAdmin)
admin.add_view(UserFlagAdmin)
```

Admin views include `after_model_change` and `after_model_delete` hooks to invalidate cache.

## FastAPI Router

```python
from kodi import get_evaluate_router

app.include_router(
    get_evaluate_router(auth_dependency=Depends(your_auth)),
    prefix="/api/v1/flags"
)
```

### Endpoint

```
GET /api/v1/flags/evaluate?names=dark-mode,new-checkout
→ {"dark-mode": true, "new-checkout": false}
```

## Package Structure

```
kodi/
├── __init__.py              # Public API exports
├── core.py                  # init(), close(), load_context(), is_enabled()
├── models.py                # SQLAlchemy models
├── cache.py                 # CacheBackend protocol
├── cache_backends.py        # Redis, InMemory, Null backends
├── context.py               # contextvar management
├── schema.py                # Schema versioning, upgrades
├── exceptions.py            # KodiError, warnings
├── admin.py                 # sqladmin ModelViews
├── router.py                # FastAPI evaluate endpoint
└── py.typed                 # PEP 561 marker

tests/
├── conftest.py
├── test_core.py
├── test_cache.py
├── test_models.py
├── test_router.py
└── test_schema.py

pyproject.toml
README.md
LICENSE
```

## Dependencies

```toml
[project]
name = "kodi"
dependencies = [
    "sqlalchemy>=2.0",
]

[project.optional-dependencies]
redis = ["redis>=4.0"]
fastapi = ["fastapi>=0.100"]
admin = ["sqladmin>=0.15"]
all = ["kodi[redis,fastapi,admin]"]
```

## Usage Modes

| Mode | Setup | Check syntax |
|------|-------|--------------|
| Middleware (recommended) | Add middleware | `kodi.is_enabled("flag")` - sync |
| Manual load | Call `load_context()` yourself | `kodi.is_enabled("flag")` - sync |
| Explicit context | None | `await kodi.is_enabled_async("flag", tenant_id=..., user_id=...)` |

## Integration Example (Generic App)

```python
# main.py
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
        tenant_id=getattr(request.state, "tenant_id", None),
        user_id=getattr(request.state, "user_id", None),
    )
    return await call_next(request)

# Usage
@app.get("/dashboard")
async def dashboard():
    if kodi.is_enabled("new-dashboard"):
        return render_new_dashboard()
    return render_old_dashboard()
```
