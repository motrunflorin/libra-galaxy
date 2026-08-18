"""Libra Galaxy backend package.

Layering (enforced by ``tests/test_architecture_boundaries.py``)::

    libra.api      HTTP surface (routers, request/response models)
        |
        v
    libra.ai       AI platform (orchestrator, agents, tools, RAG, memory)
        |
        v
    libra.domains  Deterministic banking domains (authoritative state)
        |
        v
    libra.core     Cross-cutting platform (config, errors, security, persistence)

Dependencies only point downwards. ``libra.domains`` never imports ``libra.ai``:
banking correctness must not depend on the AI layer.
"""

__version__ = "0.1.0"
