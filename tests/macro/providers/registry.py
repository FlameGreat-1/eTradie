"""Tests for ProviderRegistry (provider registration, lookup, disable/enable).

Production module: src/engine/macro/providers/registry.py
"""

from engine.macro.providers.base import BaseProvider
from engine.macro.providers.registry import ProviderRegistry
from engine.shared.models.events import ProviderCategory


class MockProvider(BaseProvider):
    """Minimal concrete provider for testing."""

    def __init__(self, name: str, category: ProviderCategory) -> None:
        super().__init__()
        self.provider_name = name
        self.category = category

    async def fetch(self):
        return {"mock": True}


class TestRegistration:
    def test_register_and_get(self):
        registry = ProviderRegistry()
        provider = MockProvider("fred", ProviderCategory.ECONOMIC_DATA)
        registry.register(provider)
        assert registry.get("fred") is provider

    def test_get_missing_returns_none(self):
        registry = ProviderRegistry()
        assert registry.get("nonexistent") is None

    def test_register_multiple(self):
        registry = ProviderRegistry()
        p1 = MockProvider("fred", ProviderCategory.ECONOMIC_DATA)
        p2 = MockProvider("te_econ", ProviderCategory.ECONOMIC_DATA)
        registry.register(p1)
        registry.register(p2)
        assert registry.get("fred") is p1
        assert registry.get("te_econ") is p2


class TestGetByCategory:
    def test_returns_matching_providers(self):
        registry = ProviderRegistry()
        econ1 = MockProvider("fred", ProviderCategory.ECONOMIC_DATA)
        econ2 = MockProvider("te_econ", ProviderCategory.ECONOMIC_DATA)
        market = MockProvider("twelve_data", ProviderCategory.MARKET_DATA)
        registry.register(econ1)
        registry.register(econ2)
        registry.register(market)

        econ_providers = registry.get_by_category(ProviderCategory.ECONOMIC_DATA)
        assert len(econ_providers) == 2
        assert econ1 in econ_providers
        assert econ2 in econ_providers

    def test_empty_category_returns_empty(self):
        registry = ProviderRegistry()
        assert registry.get_by_category(ProviderCategory.COT) == []


class TestDisableEnable:
    def test_disabled_provider_not_returned(self):
        registry = ProviderRegistry()
        provider = MockProvider("fred", ProviderCategory.ECONOMIC_DATA)
        registry.register(provider)

        registry.disable("fred")
        assert registry.get("fred") is None

    def test_disabled_excluded_from_category(self):
        registry = ProviderRegistry()
        p1 = MockProvider("fred", ProviderCategory.ECONOMIC_DATA)
        p2 = MockProvider("te_econ", ProviderCategory.ECONOMIC_DATA)
        registry.register(p1)
        registry.register(p2)

        registry.disable("fred")
        result = registry.get_by_category(ProviderCategory.ECONOMIC_DATA)
        assert len(result) == 1
        assert result[0].provider_name == "te_econ"

    def test_re_enable_restores_provider(self):
        registry = ProviderRegistry()
        provider = MockProvider("fred", ProviderCategory.ECONOMIC_DATA)
        registry.register(provider)

        registry.disable("fred")
        assert registry.get("fred") is None

        registry.enable("fred")
        assert registry.get("fred") is provider


class TestAllProviders:
    def test_returns_all_registered(self):
        registry = ProviderRegistry()
        p1 = MockProvider("fred", ProviderCategory.ECONOMIC_DATA)
        p2 = MockProvider("cftc", ProviderCategory.COT)
        registry.register(p1)
        registry.register(p2)

        all_p = registry.all_providers
        assert len(all_p) == 2
        assert "fred" in all_p
        assert "cftc" in all_p
