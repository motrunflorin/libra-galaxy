"""AI platform: orchestration, agents, tools, context, memory, RAG, telemetry.

This layer is never authoritative about money. It reads banking state only
through typed tools that call deterministic application services, and it can
never write banking state without a deterministic service performing the
change (see ``docs/AI_ARCHITECTURE.md``).
"""
