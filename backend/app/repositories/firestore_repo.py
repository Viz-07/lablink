from collections.abc import Callable
from typing import Any

from .base import COLLECTIONS, State


class FirestoreRepository:
    """Apply a demo-sized state transition in one Firestore transaction.

    A revision document serialises mutations, including queries that return no rows.
    Slot locks are inserted with create(), which enforces exclusive unit ownership.
    """

    def __init__(self, project: str, database: str) -> None:
        from google.cloud import firestore

        self._sdk = firestore
        self._client = firestore.Client(project=project, database=database)
        self._revision = self._client.collection("meta").document("seed")

    def _load(self, transaction: Any) -> State:
        return State.model_validate(
            {
                name: {
                    document.id: document.to_dict()
                    for document in self._client.collection(name).stream(transaction=transaction)
                }
                for name in COLLECTIONS
            }
        )

    def read(self) -> State:
        """Read a consistent snapshot of the collections in Firestore."""

        @self._sdk.transactional
        def snapshot(transaction: Any) -> State:
            return self._load(transaction)

        return snapshot(self._client.transaction(read_only=True))

    def transact[T](self, operation: Callable[[State], T]) -> T:
        """Apply and persist a state transition in a Firestore transaction."""

        @self._sdk.transactional
        def update(transaction: Any) -> T:
            revision = self._revision.get(transaction=transaction).to_dict() or {}
            original = self._load(transaction)
            working = original.model_copy(deep=True)
            result = operation(working)
            if working != original:
                self._save(transaction, original, working)
                transaction.set(self._revision, {"version": revision.get("version", 0) + 1})
            return result

        return update(self._client.transaction())

    def _save(self, transaction: Any, original: State, working: State) -> None:
        before, after = original.model_dump(mode="json"), working.model_dump(mode="json")
        for name in COLLECTIONS:
            collection = self._client.collection(name)
            for key in before[name].keys() - after[name].keys():
                transaction.delete(collection.document(key))
            for key, data in after[name].items():
                previous = before[name].get(key)
                if previous == data:
                    continue
                document = collection.document(key)
                if name == "slot_locks" and previous is None:
                    transaction.create(document, data)
                else:
                    transaction.set(document, data)
