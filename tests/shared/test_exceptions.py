"""Tests for the shared exception hierarchy."""

from engine.shared.exceptions import (
    CacheConnectionError,
    CacheError,
    CacheValidationError,
    ConfigurationError,
    DatabaseConnectionError,
    DatabaseError,
    ETradieBaseError,
    ProcessorError,
    ProviderAuthenticationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderValidationError,
    RAGError,
    RAGIngestError,
    RAGRetrievalError,
    StorageError,
)


class TestETradieBaseError:
    def test_message_and_details(self):
        err = ETradieBaseError("test error", details={"key": "value"})
        assert err.message == "test error"
        assert err.details == {"key": "value"}
        assert str(err) == "test error"

    def test_empty_details_default(self):
        err = ETradieBaseError("simple")
        assert err.details == {}

    def test_repr_format(self):
        err = ETradieBaseError("msg", details={"k": 1})
        r = repr(err)
        assert "ETradieBaseError" in r
        assert "msg" in r


class TestProviderErrorHierarchy:
    def test_provider_error_is_base(self):
        assert issubclass(ProviderError, ETradieBaseError)

    def test_timeout_is_provider(self):
        assert issubclass(ProviderTimeoutError, ProviderError)

    def test_rate_limit_is_provider(self):
        assert issubclass(ProviderRateLimitError, ProviderError)

    def test_auth_is_provider(self):
        assert issubclass(ProviderAuthenticationError, ProviderError)

    def test_unavailable_is_provider(self):
        assert issubclass(ProviderUnavailableError, ProviderError)

    def test_response_is_provider(self):
        assert issubclass(ProviderResponseError, ProviderError)

    def test_validation_is_provider(self):
        assert issubclass(ProviderValidationError, ProviderError)

    def test_details_propagate(self):
        err = ProviderTimeoutError(
            "timed out",
            details={"provider": "metaapi", "timeout": 30},
        )
        assert err.details["provider"] == "metaapi"
        assert isinstance(err, Exception)


class TestOtherHierarchies:
    def test_database_hierarchy(self):
        assert issubclass(DatabaseError, ETradieBaseError)
        assert issubclass(DatabaseConnectionError, DatabaseError)

    def test_cache_hierarchy(self):
        assert issubclass(CacheError, ETradieBaseError)
        assert issubclass(CacheConnectionError, CacheError)
        assert issubclass(CacheValidationError, CacheError)

    def test_processor_hierarchy(self):
        assert issubclass(ProcessorError, ETradieBaseError)

    def test_storage_hierarchy(self):
        assert issubclass(StorageError, ETradieBaseError)

    def test_configuration_hierarchy(self):
        assert issubclass(ConfigurationError, ETradieBaseError)

    def test_rag_hierarchy(self):
        assert issubclass(RAGError, ETradieBaseError)
        assert issubclass(RAGIngestError, RAGError)
        assert issubclass(RAGRetrievalError, RAGError)
