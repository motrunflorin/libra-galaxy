"""Explicit multi-step workflow state.

The reference project executed one flat turn. Libra Galaxy needs sequences
like::

    retrieve financial state -> run deterministic calculation
    -> compare against goals -> generate explanation

Workflow state is a structured, inspectable value — never a model's hidden
reasoning. Each step records its status, output and duration, so a run can be
resumed, audited or replayed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    #: Waiting for the user to confirm a prepared operation.
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    SKIPPED = "skipped"


class StepKind(str, Enum):
    TOOL_CALL = "tool_call"
    DETERMINISTIC_CALCULATION = "deterministic_calculation"
    RETRIEVAL = "retrieval"
    AGENT_GENERATION = "agent_generation"
    USER_CONFIRMATION = "user_confirmation"


@dataclass
class WorkflowStep:
    step_id: str
    kind: StepKind
    description: str
    status: StepStatus = StepStatus.PENDING
    #: Step ids that must succeed first.
    depends_on: tuple[str, ...] = ()
    duration_ms: float = 0.0
    output: dict[str, Any] | None = None
    error_code: str | None = None


@dataclass
class WorkflowRun:
    """One multi-step execution."""

    run_id: str
    steps: list[WorkflowStep] = field(default_factory=list)

    def step(self, step_id: str) -> WorkflowStep:
        for item in self.steps:
            if item.step_id == step_id:
                return item
        raise KeyError(step_id)

    def ready_steps(self) -> list[WorkflowStep]:
        """Pending steps whose dependencies have all succeeded."""
        succeeded = {item.step_id for item in self.steps if item.status is StepStatus.SUCCEEDED}
        return [
            item
            for item in self.steps
            if item.status is StepStatus.PENDING
            and all(dependency in succeeded for dependency in item.depends_on)
        ]

    @property
    def is_complete(self) -> bool:
        return all(
            item.status in (StepStatus.SUCCEEDED, StepStatus.SKIPPED, StepStatus.FAILED)
            for item in self.steps
        )

    @property
    def failed(self) -> bool:
        return any(item.status is StepStatus.FAILED for item in self.steps)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "steps": [
                {
                    "step_id": step.step_id,
                    "kind": step.kind.value,
                    "status": step.status.value,
                    "duration_ms": round(step.duration_ms, 2),
                    "error_code": step.error_code,
                }
                for step in self.steps
            ],
        }
