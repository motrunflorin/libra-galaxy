"""Shared fixtures.

Tests run entirely on in-memory repositories, so no MongoDB, no Foundry
credentials and no network access are required.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Coroutine, TypeVar

import pytest

from libra.core.config import Settings, load_settings
from libra.core.container import Container, build_container
from libra.core.money import Money
from libra.core.security.permissions import permissions_for
from libra.core.security.principal import Principal, Role
from libra.domains.accounts.memory_repository import InMemoryAccountRepository
from libra.domains.accounts.models import Account, AccountType, Subaccount, SubaccountPurpose
from libra.domains.identity.memory_repository import InMemoryUserRepository
from libra.domains.identity.models import User
from libra.domains.transactions.memory_repository import InMemoryTransactionRepository
from libra.domains.transactions.models import Direction, Transaction

T = TypeVar("T")

ALICE = "usr_alice"
BOB = "usr_bob"


def run(coroutine: Coroutine[Any, Any, T]) -> T:
    """Run an async call from a sync test (no pytest-asyncio dependency)."""
    return asyncio.run(coroutine)


def principal_for(user_id: str, role: Role = Role.CUSTOMER) -> Principal:
    return Principal(user_id=user_id, role=role, permissions=frozenset(permissions_for(role)))


def auth(user_id: str, role: str = "customer") -> dict[str, str]:
    """Development bearer token accepted only in local/test environments."""
    return {"Authorization": f"Bearer dev:{user_id}:{role}"}


@pytest.fixture
def settings() -> Settings:
    return load_settings({"LIBRA_ENV": "test"})


@pytest.fixture
def alice() -> Principal:
    return principal_for(ALICE)


@pytest.fixture
def bob() -> Principal:
    return principal_for(BOB)


@pytest.fixture
def accounts_repository() -> InMemoryAccountRepository:
    return InMemoryAccountRepository(
        accounts=[
            Account(
                account_id="acc_alice_current",
                user_id=ALICE,
                iban="RO49AAAA1B31007593840000",
                account_type=AccountType.CURRENT,
                currency="RON",
                balance=Money(250_000, "RON"),
                available_balance=Money(240_000, "RON"),
                label="Main",
            ),
            Account(
                account_id="acc_bob_current",
                user_id=BOB,
                iban="RO49BBBB1B31007593849999",
                account_type=AccountType.CURRENT,
                currency="RON",
                balance=Money(100_000, "RON"),
                available_balance=Money(100_000, "RON"),
            ),
        ],
        subaccounts=[
            Subaccount(
                subaccount_id="sub_alice_vacation",
                user_id=ALICE,
                account_id="acc_alice_current",
                purpose=SubaccountPurpose.VACATION,
                balance=Money(50_000, "RON"),
            )
        ],
    )


@pytest.fixture
def transactions_repository() -> InMemoryTransactionRepository:
    base = datetime(2026, 8, 1, tzinfo=timezone.utc)
    return InMemoryTransactionRepository(
        [
            Transaction(
                transaction_id="txn_1",
                user_id=ALICE,
                account_id="acc_alice_current",
                booked_at=base,
                amount=Money(12_000, "RON"),
                direction=Direction.DEBIT,
                merchant_raw="NETFLIX.COM",
                merchant_key="netflix",
                category_id="entertainment",
            ),
            Transaction(
                transaction_id="txn_2",
                user_id=ALICE,
                account_id="acc_alice_current",
                booked_at=base + timedelta(days=1),
                amount=Money(8_050, "RON"),
                direction=Direction.DEBIT,
                merchant_raw="KAUFLAND BUCURESTI",
                merchant_key="kaufland",
                category_id="groceries",
            ),
            Transaction(
                transaction_id="txn_3",
                user_id=ALICE,
                account_id="acc_alice_current",
                booked_at=base + timedelta(days=2),
                amount=Money(500_000, "RON"),
                direction=Direction.CREDIT,
                merchant_raw="SALARY",
                merchant_key="employer",
                category_id="income",
            ),
            Transaction(
                transaction_id="txn_bob",
                user_id=BOB,
                account_id="acc_bob_current",
                booked_at=base,
                amount=Money(99_900, "RON"),
                direction=Direction.DEBIT,
                merchant_raw="SOMETHING",
                merchant_key="something",
                category_id="other",
            ),
        ]
    )


@pytest.fixture
def users_repository() -> InMemoryUserRepository:
    return InMemoryUserRepository(
        [
            User(user_id=ALICE, email="alice@example.test", display_name="Alice"),
            User(user_id=BOB, email="bob@example.test", display_name="Bob"),
        ]
    )


@pytest.fixture
def container(
    settings: Settings,
    accounts_repository: InMemoryAccountRepository,
    transactions_repository: InMemoryTransactionRepository,
    users_repository: InMemoryUserRepository,
) -> Container:
    return build_container(
        settings,
        account_repository=accounts_repository,
        transaction_repository=transactions_repository,
        user_repository=users_repository,
    )


@pytest.fixture
def client(container: Container):
    from fastapi.testclient import TestClient

    from libra.app import create_app

    with TestClient(create_app(container.settings, container=container)) as test_client:
        yield test_client
