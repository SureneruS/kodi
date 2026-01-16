# Contributing to Kodi

Guide for AI agents and humans contributing to this project.

## Development Setup

```bash
# Clone and install
git clone https://github.com/yourusername/kodi.git
cd kodi
uv sync --all-extras

# Run checks
uv run ruff check .
uv run mypy kodi
uv run pytest
```

## Project Structure

```
kodi/
├── kodi/               # Source code
│   ├── __init__.py     # Public API exports
│   ├── core.py         # Main functionality
│   ├── models.py       # SQLAlchemy models
│   ├── cache.py        # Cache protocol
│   ├── cache_backends.py
│   ├── context.py      # contextvar management
│   ├── schema.py       # DB schema versioning
│   ├── admin.py        # sqladmin views
│   ├── router.py       # FastAPI router
│   ├── fastapi.py      # FastAPI helpers
│   └── exceptions.py   # Error types
├── tests/              # Test suite
├── docs/               # Documentation
│   └── plans/          # Design documents
├── pyproject.toml      # Package config
└── AGENTS.md           # AI agent integration guide
```

## Code Quality Requirements

All PRs must pass:

1. **Ruff** - Linting and formatting
   ```bash
   uv run ruff check .
   ```

2. **Mypy** - Type checking (strict mode)
   ```bash
   uv run mypy kodi
   ```

3. **Pytest** - All tests pass
   ```bash
   uv run pytest
   ```

## Code Conventions

### General
- Python 3.10+ syntax
- Type annotations on all functions
- No docstrings unless complexity warrants it
- No comments that restate code

### Naming
- `snake_case` for functions and variables
- `PascalCase` for classes
- `UPPER_CASE` for constants

### Async
- All database operations are `async`
- All cache operations are `async`
- Sync functions only for in-memory operations

### Imports
- Sorted by ruff (isort rules)
- `from collections.abc` for `Callable`, `Iterator`, etc.
- `from typing` only for `cast`, `Any`, `TypeVar`

### Error Handling
- Raise specific exceptions, not generic `Exception`
- Use `raise ... from e` for exception chaining
- Log warnings for recoverable issues (like unknown flags)

## Adding Features

### New API Function

1. Implement in `kodi/core.py`
2. Add to imports and `__all__` in `kodi/__init__.py`
3. Write tests in `tests/test_core.py`
4. Run all checks

### New Optional Dependency

1. Add to `pyproject.toml` under `[project.optional-dependencies]`
2. Import inside try/except with helpful error message:
   ```python
   try:
       from newlib import thing
   except ImportError as e:
       raise ImportError("newlib required. Install with: pip install kodi[newlib]") from e
   ```
3. Add `PLC0415` to file-specific ignores if needed

### Schema Changes

1. Increment `CURRENT_VERSION` in `schema.py`
2. Add upgrade function:
   ```python
   async def _upgrade_to_v2(conn: Connection) -> None:
       await conn.execute(text("ALTER TABLE ..."))

   _UPGRADES = {
       2: _upgrade_to_v2,
   }
   ```
3. Update models in `models.py`

## Lint Ignores

If you need to add a lint ignore, document why:

| Where | Rule | When to use |
|-------|------|-------------|
| `pyproject.toml` | Global ignores | Rules that conflict with project patterns |
| Per-file ignores | File-specific | External API requirements (sqladmin, etc.) |
| Inline `# noqa` | Line-specific | Last resort, must have comment explaining why |
| Inline `# type: ignore` | Type issues | Untyped libraries, protocol implementations |

## Testing

### Test Structure
```python
class TestFeatureName:
    async def test_happy_path(self, initialized_kodi, engine):
        # Arrange
        # Act
        # Assert
        pass

    async def test_edge_case(self, initialized_kodi):
        pass
```

### Fixtures
- `engine` - In-memory SQLite engine
- `initialized_kodi` - Kodi initialized with test engine, no cache

### Testing Flags
```python
async def create_flag(session, name, enabled=False) -> Flag:
    flag = Flag(name=name, enabled=enabled)
    session.add(flag)
    await session.commit()
    return flag
```

## Git Workflow

1. Create feature branch
2. Make changes
3. Run all checks
4. Commit with clear message
5. Open PR

## Questions?

Check `AGENTS.md` for architecture details or `docs/plans/` for design decisions.
