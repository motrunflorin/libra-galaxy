"""Composition root.

Everything is wired here, once, and injected downwards. Nothing in the
codebase constructs a service, repository or registry at import time — the
reference project's module-level singletons (``chat_service = ChatService()``)
made its layers impossible to test in isolation and impossible to configure
per environment.

Backend selection is configuration: ``memory`` for tests and local runs,
``mongo`` for anything deployed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from libra.ai.agents.registry import AgentRegistry
from libra.ai.context.builder import ContextBuilder
from libra.ai.context.models import ContextBudget
from libra.ai.conversations.memory_repository import InMemoryConversationRepository
from libra.ai.conversations.service import ConversationService
from libra.ai.knowledge.chunking import ChunkingPolicy
from libra.ai.orchestration.orchestrator import Orchestrator
from libra.ai.telemetry.recorder import LoggingTelemetryRecorder, TelemetryRecorder
from libra.ai.tools.banking import get_accounts, run_scenario
from libra.ai.tools.executor import ToolExecutor
from libra.ai.tools.registry import ToolRegistry
from libra.core.config import Settings
from libra.core.persistence.mongo import MongoDatabaseProvider
from libra.domains.accounts.memory_repository import InMemoryAccountRepository
from libra.domains.accounts.repository import AccountRepository
from libra.domains.accounts.service import AccountService
from libra.domains.identity.memory_repository import InMemoryUserRepository
from libra.domains.identity.repository import UserRepository
from libra.domains.identity.service import IdentityService
from libra.domains.scenarios.service import ScenarioService
from libra.domains.transactions.memory_repository import InMemoryTransactionRepository
from libra.domains.transactions.repository import TransactionRepository
from libra.domains.transactions.service import TransactionService


@dataclass
class Container:
    """Resolved application graph for one process."""

    settings: Settings
    identity: IdentityService
    accounts: AccountService
    transactions: TransactionService
    scenarios: ScenarioService
    conversations: ConversationService
    tools: ToolRegistry
    tool_executor: ToolExecutor
    agents: AgentRegistry
    orchestrator: Orchestrator
    chunking: ChunkingPolicy
    mongo: MongoDatabaseProvider | None = None


def build_container(
    settings: Settings,
    *,
    account_repository: AccountRepository | None = None,
    transaction_repository: TransactionRepository | None = None,
    user_repository: UserRepository | None = None,
    telemetry: TelemetryRecorder | None = None,
) -> Container:
    """Build the graph. Repositories may be overridden for tests."""
    mongo: MongoDatabaseProvider | None = None
    database: Any | None = None

    if settings.mongo.backend == "mongo":
        mongo = MongoDatabaseProvider(settings.mongo)
        database = mongo.database()

    accounts_repository = account_repository or _account_repository(database)
    transactions_repository = transaction_repository or InMemoryTransactionRepository()
    users_repository = user_repository or InMemoryUserRepository()

    account_service = AccountService(accounts_repository)
    transaction_service = TransactionService(transactions_repository)
    scenario_service = ScenarioService()
    identity_service = IdentityService(users_repository)
    conversation_service = ConversationService(InMemoryConversationRepository())

    tool_registry = ToolRegistry(
        (
            get_accounts.build(account_service),
            run_scenario.build(scenario_service),
        )
    )

    agents = AgentRegistry()
    orchestrator = Orchestrator(
        agents=agents,
        tools=tool_registry,
        context_builder=ContextBuilder(ContextBudget(total_chars=settings.ai.max_context_chars)),
        telemetry=telemetry or LoggingTelemetryRecorder(),
    )

    return Container(
        settings=settings,
        identity=identity_service,
        accounts=account_service,
        transactions=transaction_service,
        scenarios=scenario_service,
        conversations=conversation_service,
        tools=tool_registry,
        tool_executor=ToolExecutor(
            tool_registry, default_timeout_seconds=settings.ai.tool_timeout_seconds
        ),
        agents=agents,
        orchestrator=orchestrator,
        chunking=ChunkingPolicy(
            size_tokens=settings.rag.chunk_size_tokens,
            overlap_tokens=settings.rag.chunk_overlap_tokens,
        ),
        mongo=mongo,
    )


def _account_repository(database: Any | None) -> AccountRepository:
    if database is None:
        return InMemoryAccountRepository()
    from libra.domains.accounts.mongo_repository import MongoAccountRepository

    return MongoAccountRepository(database)
