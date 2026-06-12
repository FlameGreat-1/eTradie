"""Tests for macro collector base class and concrete collector imports.

Production module: src/engine/macro/collectors/base.py

Concrete collectors require providers + cache + db (real infrastructure).
These tests verify the import chain, class attributes, and base contract.
Full collector integration tests are deferred to the integration phase.
"""

from engine.macro.collectors.base import BaseCollector


class TestBaseCollectorContract:
    def test_base_is_abstract(self):
        """BaseCollector cannot be instantiated directly."""
        import pytest

        with pytest.raises(TypeError):
            BaseCollector([], None, None)

    def test_has_required_class_attributes(self):
        assert hasattr(BaseCollector, "collector_name")
        assert hasattr(BaseCollector, "cache_namespace")
        assert hasattr(BaseCollector, "cache_ttl")


class TestConcreteCollectorImports:
    def test_central_bank_collector(self):
        from engine.macro.collectors.central_bank.collector import CentralBankCollector

        assert CentralBankCollector is not None
        assert issubclass(CentralBankCollector, BaseCollector)

    def test_cot_collector(self):
        from engine.macro.collectors.cot.collector import COTCollector

        assert COTCollector is not None
        assert issubclass(COTCollector, BaseCollector)

    def test_economic_data_collector(self):
        from engine.macro.collectors.economic_data.collector import EconomicDataCollector

        assert EconomicDataCollector is not None
        assert issubclass(EconomicDataCollector, BaseCollector)

    def test_calendar_collector(self):
        from engine.macro.collectors.calendar.collector import CalendarCollector

        assert CalendarCollector is not None
        assert issubclass(CalendarCollector, BaseCollector)

    def test_dxy_collector(self):
        from engine.macro.collectors.dxy.collector import DXYCollector

        assert DXYCollector is not None
        assert issubclass(DXYCollector, BaseCollector)

    def test_intermarket_collector(self):
        from engine.macro.collectors.intermarket.collector import IntermarketCollector

        assert IntermarketCollector is not None
        assert issubclass(IntermarketCollector, BaseCollector)

    def test_sentiment_collector(self):
        from engine.macro.collectors.sentiment.collector import SentimentCollector

        assert SentimentCollector is not None
        assert issubclass(SentimentCollector, BaseCollector)
