import pytest

from engine.macro.providers.registry import ProviderRegistry
from engine.macro.providers.base import MacroProvider


class MockProvider(MacroProvider):
    def __init__(self, name="mock"):
        self._name = name
    
    @property
    def name(self) -> str:
        return self._name
        
    async def health_check(self) -> bool:
        return True


def test_registry_registration():
    registry = ProviderRegistry()
    provider = MockProvider("fred")
    
    registry.register("economic", provider)
    
    assert registry.get_provider("economic", "fred") is provider


def test_registry_default_selection():
    registry = ProviderRegistry()
    provider = MockProvider("alpha_vantage")
    
    registry.register("dxy", provider)
    
    # If no specific provider name requested, returns the first registered
    assert registry.get_provider("dxy") is provider


def test_registry_missing_category():
    registry = ProviderRegistry()
    
    with pytest.raises(ValueError, match="No providers registered for category"):
        registry.get_provider("fake_category")


def test_registry_missing_provider_name():
    registry = ProviderRegistry()
    provider = MockProvider("fred")
    registry.register("economic", provider)
    
    with pytest.raises(ValueError, match="Provider 'unknown' not found"):
        registry.get_provider("economic", "unknown")


def test_registry_duplicate_registration():
    registry = ProviderRegistry()
    registry.register("cot", MockProvider("cftc"))
    
    # Should overwrite silently or just allow it
    registry.register("cot", MockProvider("cftc"))
    
    # Check it still exists
    assert registry.get_provider("cot", "cftc") is not None
