from contextvars import ContextVar
from dataclasses import dataclass


@dataclass
class FlagContext:
    tenant_id: str | None
    user_id: str | None
    flags: dict[str, bool]


_context: ContextVar[FlagContext | None] = ContextVar("kodi_context", default=None)


def get_context() -> FlagContext | None:
    return _context.get()


def set_context(ctx: FlagContext) -> None:
    _context.set(ctx)


def clear_context() -> None:
    _context.set(None)
