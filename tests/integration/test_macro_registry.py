import pytest

from engine.macro.providers.base import BaseProvider
from engine.macro.providers.registry import ProviderRegistry
from engine.shared.models.events import ProviderCategory, ProviderStatus

pytestmark = pytest.mark.integration


class StubProvider(BaseProvider):
    def __init__(self, name, category):
        super().__init__()
        self.provider_name = name
        self.category = category

    async def fetch(self):
        return {"stub": True}


class TestRegistryIntegration:
    def test_register_get_disable_enable(self):
        reg = ProviderRegistry()
        p = StubProvider("fred", ProviderCategory.ECONOMIC_DATA)
        reg.register(p)
        assert reg.get("fred") is p
        reg.disable("fred")
        assert reg.get("fred") is None
        reg.enable("fred")
        assert reg.get("fred") is p

    def test_get_by_category(self):
        reg = ProviderRegistry()
        e1 = StubProvider("fred", ProviderCategory.ECONOMIC_DATA)
        e2 = StubProvider("te", ProviderCategory.ECONOMIC_DATA)
        m1 = StubProvider("twelve_data", ProviderCategory.MARKET_DATA)
        reg.register(e1)
        reg.register(e2)
        reg.register(m1)
        econ = reg.get_by_category(ProviderCategory.ECONOMIC_DATA)
        assert len(econ) == 2
        assert m1 not in econ

    def test_all_providers(self):
        reg = ProviderRegistry()
        reg.register(StubProvider("a", ProviderCategory.COT))
        reg.register(StubProvider("b", ProviderCategory.MARKET_DATA))
        assert len(reg.all_providers) == 2

    @pytest.mark.asyncio
    async def test_health_check_all(self):
        reg = ProviderRegistry()
        reg.register(StubProvider("fred", ProviderCategory.ECONOMIC_DATA))
        reg.register(StubProvider("cftc", ProviderCategory.COT))
        results = await reg.health_check_all()
        assert results["fred"] == ProviderStatus.HEALTHY
        assert results["cftc"] == ProviderStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_disabled_shows_unavailable(self):
        reg = ProviderRegistry()
        reg.register(StubProvider("fred", ProviderCategory.ECONOMIC_DATA))
        reg.disable("fred")
        results = await reg.health_check_all()
        assert results["fred"] == ProviderStatus.UNAVAILABLE


class TestCollectorImports:
    def test_all_collectors_importable(self):
        from engine.macro.collectors.calendar.collector import CalendarCollector
        from engine.macro.collectors.central_bank.collector import CentralBankCollector
        from engine.macro.collectors.cot.collector import COTCollector
        from engine.macro.collectors.dxy.collector import DXYCollector
        from engine.macro.collectors.economic_data.collector import EconomicDataCollector
        from engine.macro.collectors.intermarket.collector import IntermarketCollector
        from engine.macro.collectors.sentiment.collector import SentimentCollector

        assert all(
            [
                CentralBankCollector,
                COTCollector,
                DXYCollector,
                EconomicDataCollector,
                CalendarCollector,
                IntermarketCollector,
                SentimentCollector,
            ]
        )
