"""Gateway dependency wiring.

Builds all gateway components from the existing engine Container.
This is the single integration point between the gateway and the engine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from engine.shared.logging import get_logger
from gateway.collectors.macro_collector import MacroCollector
from gateway.collectors.ta_collector import TACollector
from gateway.config import GatewayConfig, get_gateway_config
from gateway.context.assembler import ContextAssembler
from gateway.pipeline.orchestrator import PipelineOrchestrator
from gateway.pipeline.scheduler import register_gateway_cycle
from gateway.query_builder.builder import QueryBuilder
from gateway.routing.execution_port import ExecutionPort
from gateway.routing.guards import GuardEvaluator
from gateway.routing.processor_port import ProcessorPort
from gateway.routing.router import DecisionRouter
from gateway.symbol_store import SymbolStore

if TYPE_CHECKING:
    from engine.dependencies import Container as EngineContainer

logger = get_logger(__name__)


class GatewayContainer:
    """Builds and holds all gateway components.

    Requires an already-initialized EngineContainer with:
    - ta_orchestrator
    - All 8 macro collectors
    - rag_orchestrator (via build_rag())
    - scheduler
    - cache (for SymbolStore)
    """

    def __init__(
        self,
        *,
        engine: EngineContainer,
        processor: ProcessorPort,
        execution: Optional[ExecutionPort] = None,
    ) -> None:
        self._engine = engine
        self._config = get_gateway_config()

        # Symbol Store - persists user's active symbol selection in Redis.
        # Every scheduled cycle reads from here; defaults used until user selects.
        self.symbol_store = SymbolStore(cache=engine.cache)

        # TA Collector - no symbol list here.
        # Symbols are provided by the caller at runtime via run_cycle(symbols=[...]).
        self.ta_collector = TACollector(
            ta_orchestrator=engine.ta_orchestrator,
            config=self._config,
        )

        # Macro Collector
        self.macro_collector = MacroCollector(
            cb_collector=engine.cb_collector,
            cot_collector=engine.cot_collector,
            economic_collector=engine.economic_collector,
            news_collector=engine.news_collector,
            calendar_collector=engine.calendar_collector,
            dxy_collector=engine.dxy_collector,
            intermarket_collector=engine.intermarket_collector,
            sentiment_collector=engine.sentiment_collector,
        )

        # Query Builder
        self.query_builder = QueryBuilder()

        # Context Assembler
        self.context_assembler = ContextAssembler()

        # Guard Evaluator
        self.guard_evaluator = GuardEvaluator()

        # Decision Router
        self.router = DecisionRouter(
            guard_evaluator=self.guard_evaluator,
            execution_port=execution,
        )

        # Pipeline Orchestrator
        self.orchestrator = PipelineOrchestrator(
            config=self._config,
            ta_collector=self.ta_collector,
            macro_collector=self.macro_collector,
            query_builder=self.query_builder,
            rag_orchestrator=engine.rag_orchestrator,
            context_assembler=self.context_assembler,
            processor=processor,
            router=self.router,
        )

        logger.info(
            "gateway_container_built",
            extra={
                "cycle_interval": self._config.cycle_interval_seconds,
                "cycle_timeout": self._config.cycle_timeout_seconds,
                "execution_available": execution is not None,
            },
        )

    @property
    def config(self) -> GatewayConfig:
        return self._config

    def register_scheduler(self) -> None:
        """Register the gateway cycle with the engine's scheduler."""
        register_gateway_cycle(
            scheduler=self._engine.scheduler,
            orchestrator=self.orchestrator,
            symbol_store=self.symbol_store,
            config=self._config,
        )
