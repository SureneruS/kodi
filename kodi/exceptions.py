import logging

logger = logging.getLogger("kodi")


class KodiError(Exception):
    pass


class KodiNotInitializedError(KodiError):
    def __init__(self) -> None:
        super().__init__("kodi.init() must be called before using kodi")


class KodiContextNotLoadedError(KodiError):
    def __init__(self) -> None:
        super().__init__(
            "kodi.load_context() must be called before using sync flag checks. "
            "Use kodi.is_enabled_async() for async checks without context."
        )


def warn_unknown_flag(flag_name: str) -> None:
    logger.warning(f"Unknown feature flag '{flag_name}', returning False")
