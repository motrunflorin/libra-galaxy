/**
 * Accounts feature — data access.
 *
 * A feature module owns its API calls and its components. It calls the shared
 * client and the backend's endpoints; it never recomputes a balance, a total
 * or an eligibility rule locally.
 */

import { apiRequest } from "@/lib/api/client";
import type { Account } from "@/lib/api/types";

export async function fetchAccounts(options: {
  token: string;
  locale: string;
}): Promise<Account[]> {
  const body = await apiRequest<{ accounts: Account[] }>("/accounts", options);
  return body.accounts;
}
