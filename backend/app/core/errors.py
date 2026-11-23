from typing import Any


class AppError(Exception):
    """An HTTP-safe domain failure."""

    def __init__(self, code: str, message: str, status: int = 422, **details: Any) -> None:
        super().__init__(message)
        self.code, self.message, self.status, self.details = code, message, status, details


def require(condition: object, code: str, message: str, status: int = 422) -> None:
    if not condition:
        raise AppError(code, message, status)


def find[T](collection: dict[str, T], key: str | None, label: str) -> T:
    if key is None or key not in collection:
        raise AppError("NOT_FOUND", f"{label} could not be found.", 404)
    return collection[key]
