"""
Technical Analysis (TA) module for deterministic pattern detection.

Responsibilities:
- Pull real-time market data from brokers (MT5, Twelve Data, TradingView)
- Run deterministic technical analysis (SMC and SnD frameworks)
- Identify pattern/event candidates
- Output structured technical facts for processor consumption

Does NOT perform:
- Macro interpretation
- Rulebook reasoning
- Confluence scoring
- Setup grading
- Trade decisions
- Execution logic

Architecture:
- broker/: Market data ingestion from MT5, Twelve Data, TradingView
- models/: Domain models for candles, swings, structure, liquidity, zones, candidates
- common/: Shared analyzers and services used by both SMC and SnD
- smc/: Smart Money Concepts framework detectors, zones, builders, validators
- snd/: Supply and Demand framework detectors, builders, validators
- storage/: Persistence layer for candles, snapshots, candidates
- scheduler/: Job scheduling for data refresh and analysis triggers
- orchestrator.py: Main coordination layer
"""

from engine.ta.orchestrator import TAOrchestrator

__all__ = ["TAOrchestrator"]
