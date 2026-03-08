from __future__ import annotations

from typing import Any


class ETradieBaseError(Exception):

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = details or {}

    def __repr__(self) -> str:
        cls = type(self).__name__
        return f"{cls}(message={self.message!r}, details={self.details!r})"


class ConfigurationError(ETradieBaseError):
    pass


class ProviderError(ETradieBaseError):
    pass


class ProviderTimeoutError(ProviderError):
    pass


class ProviderRateLimitError(ProviderError):
    pass


class ProviderAuthenticationError(ProviderError):
    pass


class ProviderUnavailableError(ProviderError):
    pass


class ProviderResponseError(ProviderError):
    pass


class ProviderValidationError(ProviderError):
    pass


class CollectorError(ETradieBaseError):
    pass


class CollectorAllProvidersFailedError(CollectorError):
    pass


class ProcessorError(ETradieBaseError):
    pass


class ProcessorInsufficientDataError(ProcessorError):
    pass


class StorageError(ETradieBaseError):
    pass


class StorageConnectionError(StorageError):
    pass


class StorageIntegrityError(StorageError):
    pass


class PipelineError(ETradieBaseError):
    pass


class DatabaseError(ETradieBaseError):
    pass


class DatabaseConnectionError(DatabaseError):
    pass


class DatabaseIntegrityError(DatabaseError):
    pass


class DatabaseOperationalError(DatabaseError):
    pass


class DatabaseTimeoutError(DatabaseError):
    pass


class RepositoryError(ETradieBaseError):
    pass


class CacheError(ETradieBaseError):
    pass


class CacheConnectionError(CacheError):
    pass


class CacheTimeoutError(CacheError):
    pass


class CacheValidationError(CacheError):
    pass


class HttpClientError(ETradieBaseError):
    pass


class SchedulerError(ETradieBaseError):
    pass


class SchedulerValidationError(SchedulerError):
    pass


class TracingError(ETradieBaseError):
    pass


class TracingValidationError(TracingError):
    pass
