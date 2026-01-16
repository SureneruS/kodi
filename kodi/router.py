from collections.abc import Callable
from typing import Any

try:
    from fastapi import APIRouter, Depends, Query
except ImportError as e:
    raise ImportError("fastapi package required. Install with: pip install kodi[fastapi]") from e

from kodi.context import get_context
from kodi.core import get_all
from kodi.exceptions import KodiContextNotLoadedError


def get_evaluate_router(auth_dependency: Callable[..., Any] | None = None) -> APIRouter:
    """Create a router for the evaluate endpoint.

    Args:
        auth_dependency: Optional FastAPI dependency for authentication.
                        Example: Depends(require_auth)
    """
    router = APIRouter(tags=["Feature Flags"])

    dependencies = [Depends(auth_dependency)] if auth_dependency else []

    @router.get("/evaluate", dependencies=dependencies)
    async def evaluate_flags(
        names: str | None = Query(None, description="Comma-separated flag names to evaluate"),
    ) -> dict[str, bool]:
        """Evaluate feature flags for the current context.

        If names is provided, only those flags are returned.
        Otherwise, all flags are returned.

        Requires load_context() to be called (typically via middleware).
        """
        ctx = get_context()
        if ctx is None:
            raise KodiContextNotLoadedError()

        all_flags = get_all()

        if names:
            requested = [n.strip() for n in names.split(",")]
            return {name: all_flags.get(name, False) for name in requested}

        return all_flags

    return router
