import type { ReactNode } from "react";

import { DEFAULT_LOCALE, isLocale, translator } from "@/i18n/config";
import "../globals.css";

export const metadata = {
  title: "Libra Galaxy",
  description: "AI-native digital banking",
};

/**
 * Root layout, scoped to a locale.
 *
 * Every route is reachable only under `/[locale]` (see `src/middleware.ts`),
 * so Romanian and English are addressable and `<html lang>` is always right.
 */
export default async function LocaleLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale: requested } = await params;
  const locale = isLocale(requested) ? requested : DEFAULT_LOCALE;
  const t = translator(locale);

  return (
    <html lang={locale}>
      <body>
        <header className="app-header">
          <span className="app-header__brand">{t("app.name")}</span>
        </header>
        <main className="app-main">{children}</main>
      </body>
    </html>
  );
}
