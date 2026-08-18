"""Account endpoints.

Router -> service -> repository. Ownership and permissions are enforced inside
:class:`~libra.domains.accounts.service.AccountService`, so the AI tool path
and the HTTP path share exactly one implementation of the rules.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from libra.core.api.dependencies import ContainerDep, PrincipalDep
from libra.core.api.envelope import success
from libra.domains.accounts.models import Account, Subaccount

router = APIRouter(prefix="/accounts", tags=["accounts"])


def _account_body(account: Account) -> dict[str, Any]:
    return {
        "account_id": account.account_id,
        "account_type": account.account_type.value,
        "status": account.status.value,
        "label": account.label,
        "iban_suffix": account.iban[-4:] if account.iban else "",
        "balance": account.balance.to_dict(),
        "available_balance": account.available_balance.to_dict(),
    }


def _subaccount_body(subaccount: Subaccount) -> dict[str, Any]:
    return {
        "subaccount_id": subaccount.subaccount_id,
        "account_id": subaccount.account_id,
        "purpose": subaccount.purpose.value,
        "label": subaccount.label,
        "balance": subaccount.balance.to_dict(),
    }


@router.get("")
async def list_accounts(principal: PrincipalDep, container: ContainerDep) -> dict[str, Any]:
    accounts = await container.accounts.list_accounts(principal)
    return success({"accounts": [_account_body(account) for account in accounts]})


@router.get("/{account_id}")
async def get_account(
    account_id: str, principal: PrincipalDep, container: ContainerDep
) -> dict[str, Any]:
    account = await container.accounts.get_account(principal, account_id)
    return success({"account": _account_body(account)})


@router.get("/{account_id}/subaccounts")
async def list_subaccounts(
    account_id: str, principal: PrincipalDep, container: ContainerDep
) -> dict[str, Any]:
    subaccounts = await container.accounts.list_subaccounts(principal, account_id)
    return success({"subaccounts": [_subaccount_body(item) for item in subaccounts]})
