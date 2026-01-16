# AI Agent Guide for Kodi

This document helps AI agents understand, use, and integrate with the Kodi feature flags library.

## Quick Overview

Kodi is a feature flags library for Python applications with:
- Simple on/off toggles (no percentage rollouts or complex rules)
- Multi-level overrides: platform → tenant → user (most specific wins)
- SQLAlchemy async backend (any database)
- Optional Redis caching with write-through invalidation
- FastAPI and sqladmin integration

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Application                          │
├─────────────────────────────────────────────────────────────┤
│  Middleware: kodi.load_context(tenant_id, user_id)         │
├─────────────────────────────────────────────────────────────┤
│  kodi.is_enabled("flag")  ←── reads from contextvar        │
├─────────────────────────────────────────────────────────────┤
│                    contextvar (per-request)                 │
│                    stores resolved flag states              │
├─────────────────────────────────────────────────────────────┤
│  CacheBackend (Redis/InMemory/Null)                         │
├─────────────────────────────────────────────────────────────┤
│  SQLAlchemy AsyncSession                                    │
├─────────────────────────────────────────────────────────────┤
│  Database (kodi_flags, kodi_tenant_flags, kodi_user_flags)  │
└─────────────────────────────────────────────────────────────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `kodi/core.py` | Main API: `init()`, `load_context()`, `is_enabled()`, etc. |
| `kodi/models.py` | SQLAlchemy models: `Flag`, `TenantFlag`, `UserFlag` |
| `kodi/cache.py` | `CacheBackend` protocol definition |
| `kodi/cache_backends.py` | Redis, InMemory, Null cache implementations |
| `kodi/context.py` | contextvar management for request-scoped state |
| `kodi/schema.py` | Database schema versioning and migrations |
| `kodi/admin.py` | sqladmin views with cache invalidation hooks |
| `kodi/router.py` | FastAPI `/evaluate` endpoint |
| `kodi/fastapi.py` | `require_flag()` FastAPI dependency |

## Integration Pattern

```python
# 1. Initialize at startup
await kodi.init(engine=engine, cache="redis://localhost:6379")

# 2. Load context per request (middleware)
await kodi.load_context(tenant_id="acme", user_id="user123")

# 3. Check flags (sync after load_context)
if kodi.is_enabled("new-feature"):
    use_new_feature()
```

## Flag Evaluation Logic

```python
def evaluate(flag_name, tenant_id, user_id):
    # 1. Check user override
    if user_override_exists(flag_name, tenant_id, user_id):
        return user_override.enabled

    # 2. Check tenant override
    if tenant_override_exists(flag_name, tenant_id):
        return tenant_override.enabled

    # 3. Return platform default
    if flag_exists(flag_name):
        return flag.enabled

    # 4. Unknown flag
    log_warning(f"Unknown flag: {flag_name}")
    return False
```

## Cache Invalidation

Cache is invalidated on write via sqladmin hooks:
- `FlagAdmin.after_model_change` → invalidates platform flags cache
- `TenantFlagAdmin.after_model_change` → invalidates tenant-specific cache
- `UserFlagAdmin.after_model_change` → invalidates user-specific cache

## Testing

```python
# Override flags in tests
with kodi.override({"my-flag": True}):
    assert kodi.is_enabled("my-flag")
```

## Common Tasks

### Adding a new convenience function
1. Add to `kodi/core.py`
2. Export in `kodi/__init__.py` and `__all__`
3. Add tests in `tests/test_core.py`

### Adding a new cache backend
1. Implement `CacheBackend` protocol in `kodi/cache_backends.py`
2. Add to exports if public

### Modifying the schema
1. Increment `CURRENT_VERSION` in `kodi/schema.py`
2. Add upgrade function in `_UPGRADES` dict
3. Update models in `kodi/models.py`

## Code Conventions

- Use `async`/`await` for all database and cache operations
- Type annotations required (mypy strict mode)
- No comments that just repeat what code does
- Prefer explicit over implicit (no hidden side effects)
- Follow existing patterns in the codebase
