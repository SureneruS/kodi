from collections.abc import Callable

try:
    from fastapi import HTTPException
except ImportError as e:
    raise ImportError("fastapi package required. Install with: pip install kodi[fastapi]") from e

from kodi.core import is_enabled


def require_flag(
    flag_name: str,
    raise_exc: Exception | None = None,
) -> Callable[[], None]:
    """FastAPI dependency that requires a flag to be enabled.

    Usage:
        @app.get("/beta")
        async def beta_endpoint(_=Depends(require_flag("beta-access"))):
            ...

        # With custom exception
        @app.get("/premium")
        async def premium(_=Depends(require_flag("premium", raise_exc=HTTPException(403)))):
            ...
    """
    def checker() -> None:
        if not is_enabled(flag_name):
            if raise_exc:
                raise raise_exc
            raise HTTPException(
                status_code=404,
                detail="Not found",
            )

    return checker
