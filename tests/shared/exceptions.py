from engine.shared.exceptions import (
    CacheError,
    DatabaseError,
    ETradieBaseError,
    ProcessorError,
    ProviderError,
    RAGError,
)


def test_base_error_initialization():
    """Test standard base error initialization with message and details."""
    err = ETradieBaseError("Something went wrong", details={"foo": "bar"})
    assert err.message == "Something went wrong"
    assert err.details == {"foo": "bar"}
    assert str(err) == "Something went wrong"


def test_base_error_no_details():
    """Test standard base error initialization without details defaults to empty dict."""
    err = ETradieBaseError("Simple error")
    assert err.message == "Simple error"
    assert err.details == {}


def test_base_error_repr():
    """Test standard base error repr string format."""
    err = ETradieBaseError("Message", details={"k": "v"})
    rep = repr(err)
    assert "ETradieBaseError" in rep
    assert "Message" in rep
    assert "'k': 'v'" in rep


def test_exception_hierarchy():
    """Test exception inheritance hierarchy is maintained."""
    assert issubclass(ProviderError, ETradieBaseError)
    assert issubclass(DatabaseError, ETradieBaseError)
    assert issubclass(CacheError, ETradieBaseError)
    assert issubclass(ProcessorError, ETradieBaseError)
    assert issubclass(RAGError, ETradieBaseError)


def test_specific_error_instantiation():
    """Test that sub-exceptions correctly inherit behavior."""
    err = ProviderError("Timeout from provider", details={"provider": "oanda"})
    assert err.message == "Timeout from provider"
    assert err.details["provider"] == "oanda"
    assert isinstance(err, ETradieBaseError)
    assert isinstance(err, Exception)
