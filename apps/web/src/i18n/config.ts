/**
 * Locale configuration.
 *
 * Romanian and English are first-class. Business identifiers (account types,
 * category ids, error codes) are never translated in storage — they are
 * translated here, at the edge.
 */

import en from "./messages/en.json";
import ro from "./messages/ro.json";

export const LOCALES = ["ro", "en"] as const;
export type Locale = (typeof LOCALES)[number];
export const DEFAULT_LOCALE: Locale = "ro";

const MESSAGES: Record<Locale, Record<string, string>> = { ro, en };

export function isLocale(value: string): value is Locale {
  return (LOCALES as readonly string[]).includes(value);
}

/** Look up a translation key, falling back to the key itself when missing. */
export function translator(locale: Locale) {
  const messages = MESSAGES[locale];
  return (key: string): string => messages[key] ?? key;
}
