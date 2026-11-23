from ..core.config import Settings
from .base import Repository
from .firestore_repo import FirestoreRepository
from .memory_repo import InMemoryRepository


def build_repository(settings: Settings) -> Repository:
    """Select the repository implementation for the configured storage mode."""
    if settings.storage == "firestore":
        return FirestoreRepository(settings.gcp_project, settings.firestore_database)
    return InMemoryRepository()
