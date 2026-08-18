"""Version 1 router assembly.

New resource groups are added here. Versioning strategy: breaking changes go
to ``/api/v2`` with its own router package; ``v1`` keeps its contract.
"""

from __future__ import annotations

from fastapi import APIRouter

from libra.api.v1.routes import accounts, assistant, health

router = APIRouter()
router.include_router(health.router)
router.include_router(accounts.router)
router.include_router(assistant.router)
