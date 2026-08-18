# API Conventions

Base path: `/api/v1`. Every endpoint returns the same envelope, always with the
correct HTTP status code.

---

## 1. Response envelope

**Success**

```json
{
  "success": true,
  "message": "OK",
  "body": { "accounts": [] },
  "request_id": "req_9f2c1a4b8e6d3f70"
}
```

**Failure**

```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested resource was not found.",
    "details": null
  },
  "request_id": "req_9f2c1a4b8e6d3f70"
}
```

The envelope never replaces the status code — a 404 is a 404. Clients branch on
`error.code`, log `request_id`, and show `error.message` only as a fallback
(the UI prefers its own translated string keyed by the code).

`request_id` is echoed in the `X-Request-ID` header and accepted from the
client, so a frontend trace and a backend trace share one identifier.

---

## 2. Error codes

Stable and machine-readable; renaming one is a breaking change.

| Code | Status | Meaning |
| --- | --- | --- |
| `VALIDATION_ERROR` | 422 | Input failed validation; `details.fields` lists the fields |
| `AUTH_REQUIRED` | 401 | No credentials presented |
| `AUTH_INVALID` | 401 | Credentials present but not valid |
| `PERMISSION_DENIED` | 403 | Authenticated, not authorized |
| `RESOURCE_NOT_FOUND` | 404 | Missing — or belongs to someone else (see below) |
| `CONFLICT` | 409 | Conflicts with current state |
| `CONFIRMATION_REQUIRED` | 409 | The user must explicitly confirm |
| `IDEMPOTENCY_CONFLICT` | 409 | Same key, different payload |
| `RATE_LIMITED` | 429 | Too many requests |
| `PERSISTENCE_ERROR` | 503 | Storage unavailable |
| `CONFIGURATION_ERROR` | 500 | Service misconfigured |
| `AI_PROVIDER_ERROR` | 502 | Foundry returned an error |
| `AI_PROVIDER_UNAVAILABLE` | 503 | Foundry unreachable/unconfigured — **no fallback** |
| `AGENT_NOT_AVAILABLE` | 503 | No agent can handle this request yet |
| `AGENT_EXECUTION_ERROR` | 502 | The agent failed |
| `TOOL_NOT_ELIGIBLE` | 403 | Capability not available in this context |
| `TOOL_TIMEOUT` | 504 | A capability exceeded its budget |
| `TOOL_EXECUTION_ERROR` | 502 | A capability failed |
| `RETRIEVAL_ERROR` | 503 | Knowledge retrieval failed |
| `VOICE_SERVICE_ERROR` | 502 | Voice service failed |
| `INTERNAL_ERROR` | 500 | Unexpected; details are logged, never returned |

### Not-found vs forbidden

Customer read paths return `RESOURCE_NOT_FOUND` for a resource owned by
somebody else. Returning `PERMISSION_DENIED` would confirm the identifier
exists, which turns any endpoint into an enumeration oracle.
`PERMISSION_DENIED` is used when the caller lacks a *capability* they could
legitimately be told about ("you cannot execute payments").

---

## 3. Authentication

```http
Authorization: Bearer <access-token>
Accept-Language: ro
X-Request-ID: req_web_1a2b3c4d5e6f7g8h   (optional)
```

Phase 0 accepts a development scheme, `Bearer dev:<user_id>:<role>`, refused
outside `local`/`test`. It exists so the authorization boundary is real and
testable before the Phase 1 login flow lands. Replacing it changes only
`get_principal`; everything downstream already depends on `Principal`.

---

## 4. Money on the wire

```json
{ "minor_units": 250000, "currency": "RON", "amount": "2500.00" }
```

`minor_units` is the value; `amount` is a convenience string for display.
Clients must never do arithmetic on `amount`. Formatting is locale-dependent,
the value is not: a Romanian and an English user see the same number of bani.

---

## 5. Localization

The server picks a language from `Accept-Language` (`ro`, `en`, `ro-RO`,
weighted lists), defaulting to `ro`. It affects only generated natural-language
text — assistant answers, notification copy.

Everything else stays as stable identifiers: `account_type: "current"`,
`category_id: "groceries"`, `error.code`. The frontend translates them. Storing
a translated label would make the data unqueryable across languages.

---

## 6. Pagination

```http
GET /api/v1/transactions?limit=50&offset=0
```

```json
{ "items": [], "total": 128, "limit": 50, "offset": 0, "has_more": true }
```

`limit` is clamped server-side (max 200). Clients must not assume an
unclamped value was honoured.

---

## 7. Idempotency

Mutating endpoints accept an `Idempotency-Key` header and enforce it in the
database (`payments_idempotency_unique`), not in application memory. Replaying
the same key with the same payload returns the original result; a different
payload returns `IDEMPOTENCY_CONFLICT`.

---

## 8. Confirmation

Sensitive operations are two-step:

```text
POST /payments/prepare   → 200, a draft with what will happen
POST /payments/confirm   → 200, executed  |  409 CONFIRMATION_REQUIRED
```

The assistant may *prepare* an operation. Confirmation is always an explicit
user action against a deterministic endpoint — never a model deciding the user
"seemed to agree".

---

## 9. Versioning

`/api/v1` is a stable contract. Additive changes (new fields, new endpoints)
ship in v1; breaking changes (removed or renamed fields, changed types,
changed error semantics) require `/api/v2`. Error codes are part of the
contract.

---

## 10. Endpoints today

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/health` | none | Liveness, environment, wired capabilities |
| GET | `/accounts` | required | The caller's accounts |
| GET | `/accounts/{id}` | required | One account the caller owns |
| GET | `/accounts/{id}/subaccounts` | required | Subaccounts of that account |
| POST | `/assistant/messages` | required | Run the orchestration pipeline |
| GET | `/assistant/capabilities` | required | Agents and tools available to this caller |

`/health` reports deployment *names* and whether Foundry is configured. It
never reports endpoints, keys, connection strings or user data.
