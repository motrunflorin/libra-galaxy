"""The authenticated caller.

A ``Principal`` is produced once per request by the authentication layer and
then flows unchanged into services, tools and agents. Nothing downstream may
construct or widen a principal: privileges only ever narrow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from libra.core.locale import DEFAULT_LOCALE, Locale


class Role(str, Enum):
    """Coarse role. Fine-grained rights live in :class:`Permission`."""

    CUSTOMER = "customer"
    SUPPORT = "support"
    COMPLIANCE_OFFICER = "compliance_officer"
    ADMIN = "admin"
    #: Non-human caller (scheduled jobs, proactive engagement runs).
    SERVICE = "service"


class Permission(str, Enum):
    """Server-side rights checked on every sensitive operation."""

    ACCOUNTS_READ = "accounts:read"
    TRANSACTIONS_READ = "transactions:read"
    PAYMENTS_PREPARE = "payments:prepare"
    PAYMENTS_EXECUTE = "payments:execute"
    SAVINGS_MANAGE = "savings:manage"
    SUBSCRIPTIONS_MANAGE = "subscriptions:manage"
    DOCUMENTS_READ = "documents:read"
    DOCUMENTS_UPLOAD = "documents:upload"
    ASSISTANT_USE = "assistant:use"
    KYC_REVIEW = "kyc:review"
    ADMIN_USERS = "admin:users"
    ADMIN_OBSERVABILITY = "admin:observability"


@dataclass(frozen=True)
class Principal:
    """Identity + authorization context for one request."""

    user_id: str
    role: Role
    permissions: frozenset[Permission] = field(default_factory=frozenset)
    locale: Locale = DEFAULT_LOCALE
    session_id: str | None = None

    def has(self, permission: Permission) -> bool:
        return permission in self.permissions

    def owns(self, owner_user_id: str) -> bool:
        """Resource ownership check — the default rule for customer data."""
        return self.user_id == owner_user_id

    @property
    def is_staff(self) -> bool:
        return self.role in (Role.SUPPORT, Role.COMPLIANCE_OFFICER, Role.ADMIN)
