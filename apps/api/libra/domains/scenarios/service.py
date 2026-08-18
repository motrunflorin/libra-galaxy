"""Scenario application service.

Wraps the pure engine with authorization. CashPlay is read-only by
construction: no repository is written and no account is touched.
"""

from __future__ import annotations

from libra.core.security.authorization import require_permission
from libra.core.security.principal import Permission, Principal
from libra.domains.scenarios.engine import ScenarioEngine
from libra.domains.scenarios.models import ScenarioInput, ScenarioProjection


class ScenarioService:
    def __init__(self, engine: ScenarioEngine | None = None) -> None:
        self._engine = engine or ScenarioEngine()

    async def simulate(self, principal: Principal, scenario: ScenarioInput) -> ScenarioProjection:
        require_permission(principal, Permission.ACCOUNTS_READ)
        return self._engine.project(scenario)
