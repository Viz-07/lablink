from collections.abc import Callable
from threading import RLock

from .base import State


class InMemoryRepository:
    """Keep isolated snapshots and commit writes atomically in one process."""

    def __init__(self, state: State | None = None) -> None:
        self._state = state.model_copy(deep=True) if state else State()
        self._lock = RLock()

    def read(self) -> State:
        with self._lock:
            return self._state.model_copy(deep=True)

    def transact[T](self, operation: Callable[[State], T]) -> T:
        with self._lock:
            working = self._state.model_copy(deep=True)
            result = operation(working)
            self._state = working
            return result
