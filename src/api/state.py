from __future__ import annotations

SESSION_STORE: dict[str, dict] = {}

SESSION_TTL_HOURS = 4


class SessionNotFoundError(Exception):
    pass


class LLMError(Exception):
    def __init__(self, message: str, raw_result: object = None) -> None:
        super().__init__(message)
        self.raw_result = raw_result
