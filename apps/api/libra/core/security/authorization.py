"""Authorization guards.

Guards raise rather than return booleans so a forgotten check cannot silently
pass. They are used by application services — never only at the HTTP edge and
never only in the frontend.
"""

from __future__ import annotations

from libra.core.errors import PermissionDeniedError, ResourceNotFoundError
from libra.core.security.principal import Permission, Principal


def require_permission(principal: Principal, permission: Permission) -> None:
    if not principal.has(permission):
        raise PermissionDeniedError()


def require_ownership(principal: Principal, owner_user_id: str) -> None:
    """Assert the principal owns the resource.

    Staff roles are *not* silently allowed here: a staff read path must call
    :func:`require_permission` with its own explicit permission, so cross-user
    access is always deliberate and auditable.
    """
    if not principal.owns(owner_user_id):
        raise PermissionDeniedError()

