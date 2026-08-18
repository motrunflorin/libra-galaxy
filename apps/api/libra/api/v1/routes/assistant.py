"""Galaxy AI assistant endpoint.

The route is thin on purpose: it validates the request, hands it to the
orchestrator and serialises the user-facing part of the result. The internal
trace stays in telemetry — a banking customer never receives execution
internals.

Until Phase 3 registers the first agent implementation, this endpoint answers
``503 AGENT_NOT_AVAILABLE``. That is the intended behaviour: the pipeline is
real, and it fails cleanly and observably instead of inventing an answer.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from libra.ai.orchestration.models import OrchestrationRequest
from libra.core.api.dependencies import ContainerDep, LocaleDep, PrincipalDep
from libra.core.api.envelope import success
from libra.core.request_context import get_request_id

router = APIRouter(prefix="/assistant", tags=["assistant"])


class AssistantMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None
    #: Set by the client when the user confirms a prepared operation.
    confirm: bool = False


@router.post("/messages")
async def send_message(
    payload: AssistantMessageRequest,
    principal: PrincipalDep,
    container: ContainerDep,
    locale: LocaleDep,
) -> dict[str, Any]:
    result = await container.orchestrator.handle(
        OrchestrationRequest(
            principal=principal,
            message=payload.message,
            conversation_id=payload.conversation_id,
            locale=locale,
            user_confirmed=payload.confirm,
            request_id=get_request_id() or "",
        )
    )
    return success(
        {
            "reply": result.text,
            "agent_id": result.agent_id,
            "intent": result.intent.value,
            "conversation_id": result.conversation_id,
            "citations": list(result.citations),
            "data": result.data,
            "pending_confirmation": result.pending_confirmation,
        }
    )


@router.get("/capabilities")
async def capabilities(principal: PrincipalDep, container: ContainerDep) -> dict[str, Any]:
    """What the assistant can do for *this* caller.

    Tool metadata is filtered by the caller's permissions, so the UI can
    explain unavailable capabilities without leaking the full catalogue.
    """
    agents = [
        {
            "agent_id": spec.agent_id,
            "display_name": spec.display_name,
            "purpose": spec.purpose,
            "available": container.agents.is_implemented(spec.agent_id),
        }
        for spec in container.agents.specs()
    ]
    tools = [
        {
            "name": definition.name,
            "description": definition.description,
            "requires_confirmation": definition.requires_confirmation,
        }
        for definition in container.tools.all()
        if definition.required_permissions <= principal.permissions
    ]
    return success({"agents": agents, "tools": tools})
