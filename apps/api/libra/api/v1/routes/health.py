"""Liveness and readiness.

``/health`` is unauthenticated and deliberately says nothing about
configuration secrets, users or data — only whether the process is up and
which capabilities are wired.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from libra.core.api.dependencies import ContainerDep
from libra.core.api.envelope import success

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(container: ContainerDep) -> dict[str, Any]:
    settings = container.settings
    return success(
        {
            "status": "ok",
            "environment": settings.app.environment.value,
            "persistence_backend": settings.mongo.backend,
            "ai": {
                # Deployment names, never endpoints or keys.
                "chat_deployment": settings.foundry.chat_deployment,
                "embedding_deployment": settings.foundry.embedding_deployment,
                "configured": settings.foundry.is_configured,
            },
            "capabilities": {
                "registered_tools": len(container.tools),
                "declared_agents": len(container.agents.specs()),
                "implemented_agents": sum(
                    1
                    for spec in container.agents.specs()
                    if container.agents.is_implemented(spec.agent_id)
                ),
            },
        },
        message="Service is healthy.",
    )
