"""Multi-user isolation: the boundary the reference project did not have."""

from __future__ import annotations

import pytest

from libra.core.errors import PermissionDeniedError, ResourceNotFoundError
from libra.core.security.principal import Permission, Principal, Role
from tests.conftest import ALICE, auth, run


def test_user_only_sees_own_accounts(client) -> None:
    body = client.get("/api/v1/accounts", headers=auth(ALICE)).json()["body"]
    ids = {account["account_id"] for account in body["accounts"]}
    assert ids == {"acc_alice_current"}


def test_other_users_account_is_not_found(client) -> None:
    response = client.get("/api/v1/accounts/acc_bob_current", headers=auth(ALICE))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_service_enforces_ownership_even_without_http(container, alice) -> None:
    with pytest.raises(ResourceNotFoundError):
        run(container.accounts.get_account(alice, "acc_bob_current"))


def test_missing_permission_is_denied(container) -> None:
    stripped = Principal(user_id=ALICE, role=Role.CUSTOMER, permissions=frozenset())
    with pytest.raises(PermissionDeniedError):
        run(container.accounts.list_accounts(stripped))


def test_support_role_cannot_move_money() -> None:
    from libra.core.security.permissions import permissions_for

    support = permissions_for(Role.SUPPORT)
    assert Permission.PAYMENTS_EXECUTE not in support
    assert Permission.ACCOUNTS_READ in support


def test_transaction_totals_are_scoped_to_the_owner(container, alice, bob) -> None:
    from datetime import datetime, timezone

    since = datetime(2026, 7, 1, tzinfo=timezone.utc)
    until = datetime(2026, 9, 1, tzinfo=timezone.utc)

    alice_summary = run(
        container.transactions.spending_summary(alice, since=since, until=until, currency="RON")
    )
    bob_summary = run(
        container.transactions.spending_summary(bob, since=since, until=until, currency="RON")
    )

    assert alice_summary.total_spent.minor_units == 12_000 + 8_050
    assert bob_summary.total_spent.minor_units == 99_900
    assert alice_summary.transaction_count == 3
