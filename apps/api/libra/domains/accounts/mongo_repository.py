"""MongoDB account repository.

The only place in the accounts domain that knows about documents and BSON.
Queries always filter on ``user_id`` first, matching ``accounts_user_status``
in :mod:`libra.core.persistence.indexes`.
"""

from __future__ import annotations

from typing import Any, Sequence

from libra.core.money import Money
from libra.domains.accounts.models import (
    Account,
    AccountStatus,
    AccountType,
    Subaccount,
    SubaccountPurpose,
)
from libra.domains.accounts.repository import AccountRepository

COLLECTION = "accounts"
SUBACCOUNT_COLLECTION = "subaccounts"


def _to_account(document: dict[str, Any]) -> Account:
    currency = str(document["currency"])
    return Account(
        account_id=str(document["_id"]),
        user_id=str(document["user_id"]),
        iban=str(document["iban"]),
        account_type=AccountType(document["account_type"]),
        currency=currency,
        balance=Money(int(document["balance_minor_units"]), currency),
        available_balance=Money(int(document["available_balance_minor_units"]), currency),
        status=AccountStatus(document.get("status", AccountStatus.ACTIVE.value)),
        label=str(document.get("label", "")),
        opened_at=document.get("opened_at"),
    )


def _to_subaccount(document: dict[str, Any]) -> Subaccount:
    currency = str(document["currency"])
    return Subaccount(
        subaccount_id=str(document["_id"]),
        user_id=str(document["user_id"]),
        account_id=str(document["account_id"]),
        purpose=SubaccountPurpose(document["purpose"]),
        balance=Money(int(document["balance_minor_units"]), currency),
        label=str(document.get("label", "")),
    )


class MongoAccountRepository(AccountRepository):
    def __init__(self, database: Any) -> None:
        self._accounts = database[COLLECTION]
        self._subaccounts = database[SUBACCOUNT_COLLECTION]

    async def list_for_user(self, user_id: str) -> Sequence[Account]:
        cursor = self._accounts.find({"user_id": user_id}).sort("opened_at", 1)
        return [_to_account(document) async for document in cursor]

    async def get_for_user(self, user_id: str, account_id: str) -> Account | None:
        document = await self._accounts.find_one({"_id": account_id, "user_id": user_id})
        return _to_account(document) if document else None

    async def list_subaccounts(self, user_id: str, account_id: str) -> Sequence[Subaccount]:
        cursor = self._subaccounts.find({"user_id": user_id, "account_id": account_id})
        return [_to_subaccount(document) async for document in cursor]
