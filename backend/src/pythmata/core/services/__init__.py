"""Core services for process execution."""

from enum import Enum, auto

from dependency_injector.containers import DeclarativeContainer
from dependency_injector.providers import Provider, Self, Singleton

from pythmata.core.services.registry import get_service_task_registry
from pythmata.core.services.standard import StandardServiceRegistry


class ServiceType(Enum):
    """Available service types."""

    STANDARD = auto()
    VERSIONING = auto()


class ServiceRegistry(DeclarativeContainer):
    """Container for core services."""

    @classmethod
    def standard(cls) -> "ServiceRegistry":
        """Get the standard service registry."""
        registry = cls()
        registry.registry = Provider(StandardServiceRegistry)
        return registry

    @classmethod
    def versioning(cls) -> "ServiceRegistry":
        """Get the versioning service registry."""
        from pythmata.core.services.versioning import (
            VersionManager,
            VersionDiff,
            VersionMetadata,
            ConflictResolver,
        )
        
        registry = cls()
        registry.version_manager = Provider(VersionManager)
        registry.version_diff = Provider(VersionDiff)
        registry.version_metadata = Provider(VersionMetadata)
        registry.conflict_resolver = Provider(ConflictResolver)
        return registry
