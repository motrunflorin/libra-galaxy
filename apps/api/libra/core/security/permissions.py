"""Role to permission mapping.

Kept as data so it can be tested and later moved into configuration or a
database without touching call sites.
"""

from __future__ import annotations

from libra.core.security.principal import Permission, Role

_CUSTOMER_PERMISSIONS = frozenset(
    {
        Permission.ACCOUNTS_READ,
        Permission.TRANSACTIONS_READ,
        Permission.PAYMENTS_PREPARE,
        Permission.PAYMENTS_EXECUTE,
        Permission.SAVINGS_MANAGE,
        Permission.SUBSCRIPTIONS_MANAGE,
        Permission.DOCUMENTS_READ,
        Permission.DOCUMENTS_UPLOAD,
        Permission.ASSISTANT_USE,
    }
)

#: Support sees a customer's read-only banking context, never their money.
_SUPPORT_PERMISSIONS = frozenset(
    {
        Permission.ACCOUNTS_READ,
        Permission.TRANSACTIONS_READ,
        Permission.DOCUMENTS_READ,
    }
)

_COMPLIANCE_PERMISSIONS = _SUPPORT_PERMISSIONS | frozenset({Permission.KYC_REVIEW})

_ADMIN_PERMISSIONS = _COMPLIANCE_PERMISSIONS | frozenset(
    {Permission.ADMIN_USERS, Permission.ADMIN_OBSERVABILITY}
)

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.CUSTOMER: _CUSTOMER_PERMISSIONS,
    Role.SUPPORT: _SUPPORT_PERMISSIONS,
    Role.COMPLIANCE_OFFICER: _COMPLIANCE_PERMISSIONS,
    Role.ADMIN: _ADMIN_PERMISSIONS,
    Role.SERVICE: frozenset({Permission.ASSISTANT_USE}),
}


def permissions_for(role: Role) -> frozenset[Permission]:
    return ROLE_PERMISSIONS.get(role, frozenset())
