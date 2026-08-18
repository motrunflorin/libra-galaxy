import { DEFAULT_LOCALE, isLocale, translator } from "@/i18n/config";

/**
 * Dashboard shell.
 *
 * Feature modules (accounts, transactions, payments, savings, CashPlay,
 * Galaxy AI, documents, admin) mount here as they are implemented. Rendering
 * real account data requires the Phase 1 authentication flow to supply a
 * token, so this page stays a shell rather than displaying invented data.
 */
export default async function DashboardPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale: requested } = await params;
  const locale = isLocale(requested) ? requested : DEFAULT_LOCALE;
  const t = translator(locale);

  return (
    <section className="dashboard">
      <h1>{t("nav.dashboard")}</h1>
      <p>{t("accounts.title")}</p>
    </section>
  );
}
