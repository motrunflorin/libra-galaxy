/**
 * Accounts feature — presentation.
 *
 * Server component: the balance is rendered from the value the backend
 * returned, formatted for the active locale.
 */

import { formatMoney } from "@/lib/api/format";
import type { Locale } from "@/i18n/config";
import { translator } from "@/i18n/config";
import type { Account } from "@/lib/api/types";

export function AccountList({ accounts, locale }: { accounts: Account[]; locale: Locale }) {
  const t = translator(locale);

  if (accounts.length === 0) {
    return <p className="empty-state">{t("accounts.empty")}</p>;
  }

  return (
    <ul className="account-list">
      {accounts.map((account) => (
        <li key={account.account_id} className="account-card">
          <span className="account-card__label">
            {account.label || t(`accountType.${account.account_type}`)}
          </span>
          <span className="account-card__iban">•••• {account.iban_suffix}</span>
          <strong className="account-card__balance">
            {formatMoney(account.balance, locale)}
          </strong>
          <span className="account-card__available">
            {t("accounts.available")}: {formatMoney(account.available_balance, locale)}
          </span>
        </li>
      ))}
    </ul>
  );
}
