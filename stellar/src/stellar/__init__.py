"""Stellar Agents: the Stellar layer built beside upstream TradingAgents.

Foundation Phase 1 provides the core only: typed contracts, the event envelope
and catalogue, the append-only journal, configuration and the agent registry.
There is no market data, no LLM call, no risk engine and no broker here.

Stellar may import ``tradingagents``; ``tradingagents`` never imports Stellar.
"""

__version__ = "0.1.0"
