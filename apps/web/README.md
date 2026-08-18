# Libra Galaxy Web

Next.js frontend. A presentation layer over the FastAPI backend — it formats,
translates and navigates. It never decides what a balance is or whether an
operation is allowed.

```bash
npm install
npm run dev        # http://localhost:3000
npm run typecheck
```

Requires Node 20+.

## Layout

```text
src/
  app/[locale]/     routes, locale-scoped (ro | en)
  features/<name>/  feature modules: api.ts + components
  lib/api/          the single typed client: envelope, errors, request ids
  lib/api/format.ts locale-aware money formatting
  i18n/             ro.json / en.json + negotiation
```

## Rules

1. **No banking logic.** Do not recompute a total, a score or an eligibility
   rule that the backend already computes. If a number is missing from a
   response, add it to the endpoint.
2. **All API calls go through `lib/api/client.ts`** — it attaches the auth
   header, the locale, a request id, and unwraps the response envelope into
   data or a typed `ApiError`.
3. **Money arithmetic uses `minor_units`.** `amount` is a display string.
4. **Every user-visible string is a translation key**, present in both
   `ro.json` and `en.json`. Stable identifiers from the API
   (`account_type`, `category_id`, `error.code`) are translated here, never
   stored translated.
5. **Handle the four states**: loading, empty, error, success. Error copy is
   keyed by `error.code`, with `error.generic` as the fallback.
6. **Responsive from the start.** Desktop first, mobile fully usable.
7. **Never render an internal execution trace.** The backend does not send one;
   do not invent one.

## Design direction

Space-themed identity — stars, planets, orbits — under a banking constraint:
contrast, legibility and calm come first. Tokens live in `app/globals.css`; the
visual pass is a later phase.
