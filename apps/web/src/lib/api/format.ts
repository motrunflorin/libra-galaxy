/**
 * Locale-aware formatting of exact amounts.
 *
 * Formatting is presentation only: `minor_units` stays the source of truth,
 * so a Romanian and an English user always see the same number of bani.
 */

import type { Money } from "./types";

const MINOR_UNITS_PER_MAJOR = 100;

export function formatMoney(money: Money, locale: string): string {
  return new Intl.NumberFormat(locale === "ro" ? "ro-RO" : "en-GB", {
    style: "currency",
    currency: money.currency,
  }).format(money.minor_units / MINOR_UNITS_PER_MAJOR);
}
