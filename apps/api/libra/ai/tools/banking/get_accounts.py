"""``get_accounts`` — authoritative balances for the signed-in user.

This is how an agent answers "what is my balance?". Retrieval and conversation
memory are never acceptable sources for that answer.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from libra.ai.tools.contract import RiskLevel, SideEffect, ToolContext, ToolDefinition
from libra.core.security.principal import Permission
from libra.domains.accounts.service import AccountService

TOOL_NAME = "get_accounts"


class GetAccountsInput(BaseModel):
    include_subaccounts: bool = Field(
        default=False, description="Also return purpose-oriented subaccounts."
    )


class AccountView(BaseModel):
    account_id: str
    account_type: str
    currency: str
    #: Exact integer amount; the model is never asked to do the arithmetic.
    balance_minor_units: int
    available_balance_minor_units: int
    label: str = ""
    status: str = "active"
    #: Masked; the full IBAN is not needed to answer questions about money.
    iban_suffix: str = ""


class SubaccountView(BaseModel):
    subaccount_id: str
    account_id: str
    purpose: str
    balance_minor_units: int
    currency: str
    label: str = ""


class GetAccountsOutput(BaseModel):
    accounts: list[AccountView]
    subaccounts: list[SubaccountView] = Field(default_factory=list)
    source: str = "AccountService"


def build(service: AccountService) -> ToolDefinition:
    async def handler(context: ToolContext, arguments: GetAccountsInput) -> GetAccountsOutput:
        accounts = await service.list_accounts(context.principal)
        views = [
            AccountView(
                account_id=account.account_id,
                account_type=account.account_type.value,
                currency=account.currency,
                balance_minor_units=account.balance.minor_units,
                available_balance_minor_units=account.available_balance.minor_units,
                label=account.label,
                status=account.status.value,
                iban_suffix=account.iban[-4:] if account.iban else "",
            )
            for account in accounts
        ]

        subaccount_views: list[SubaccountView] = []
        if arguments.include_subaccounts:
            for account in accounts:
                for item in await service.list_subaccounts(context.principal, account.account_id):
                    subaccount_views.append(
                        SubaccountView(
                            subaccount_id=item.subaccount_id,
                            account_id=item.account_id,
                            purpose=item.purpose.value,
                            balance_minor_units=item.balance.minor_units,
                            currency=item.balance.currency,
                            label=item.label,
                        )
                    )

        return GetAccountsOutput(accounts=views, subaccounts=subaccount_views)

    return ToolDefinition(
        name=TOOL_NAME,
        description="Return the signed-in user's accounts and exact balances.",
        input_model=GetAccountsInput,
        output_model=GetAccountsOutput,
        handler=handler,
        allowed_agents=frozenset({"financial_advisor", "transaction_intelligence", "engagement"}),
        required_permissions=frozenset({Permission.ACCOUNTS_READ}),
        side_effect=SideEffect.READ_ONLY,
        risk_level=RiskLevel.LOW,
        tags=("accounts", "authoritative"),
    )
