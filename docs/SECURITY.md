# Security

Libra Galaxy is multi-user from the foundation. This is the largest single
improvement over the reference project, which had no users, no authentication
and no authorization: any client-supplied session id reached any session.

---

## 1. Identity and authorization

A `Principal` is built once per request and flows unchanged into services,
tools and agents. Nothing downstream constructs or widens one — privileges only
narrow.

```python
Principal(user_id, role, permissions, locale, session_id)
```

| Role | Permissions |
| --- | --- |
| `customer` | Own accounts, transactions, payments, savings, subscriptions, documents, assistant |
| `support` | Read-only accounts, transactions, documents. **No money movement** |
| `compliance_officer` | Support permissions + `kyc:review` |
| `admin` | Compliance permissions + `admin:users`, `admin:observability` |
| `service` | `assistant:use` only (scheduled/proactive runs) |

Guards raise instead of returning booleans, so a forgotten check cannot
silently pass:

```python
require_permission(principal, Permission.ACCOUNTS_READ)
require_ownership(principal, account.user_id)
```

Staff roles are **not** silently allowed through ownership checks. A staff read
path must use its own explicit permission, so every cross-user access is
deliberate and auditable.

### Where authorization lives

In application services — not in routers, not in the frontend, not in prompts.
The HTTP path and the AI tool path call the same service methods and therefore
share exactly one implementation of the rules. `test_routers_do_not_import_repositories`
prevents a router from reaching around a service.

### Isolation in queries

Every read for customer data filters on the owner in the query, and every
collection is indexed owner-first. Loading first and checking afterwards is not
acceptable: it leaks through timing, error shapes and log volume.

---

## 2. The AI safety boundary

**Model output alone can never**: change a balance, execute a transfer, modify
permissions, authorize a user, change account ownership, alter ledger state,
cancel a product, or make an unrestricted compliance decision.

Enforcement is structural, not instructional — a prompt cannot grant itself a
capability:

| Control | Mechanism |
| --- | --- |
| Agents cannot reach the database | Import rule, verified by an architecture test |
| Agents cannot reach services directly | Only typed tools bridge, and tools call services |
| Tools declare their own limits | `allowed_agents`, `required_permissions`, `side_effect`, `risk_level`, `requires_confirmation` |
| Eligibility is decided outside the model | `ai/tools/eligibility.py`, re-checked at execution |
| Mutating tools require confirmation | Enforced at tool construction; a mutating tool without it fails to build |
| High-risk intents never reach an agent unconfirmed | `RiskClassifier` → `CONFIRMATION_REQUIRED` |
| Agents cannot exceed their contract | `Orchestrator._validate` after execution |
| Every capability use is recorded | `ToolInvocationRecord` with the selection reason |

### Confirmation

Two-step by design: the assistant may *prepare*, the user confirms against a
deterministic endpoint. A model deciding the user "seemed to agree" is not
confirmation.

### Never claim success

An agent may not state that something happened unless the deterministic
operation returned success. This is stated in each agent's prohibitions and is
an evaluation assertion.

---

## 3. Data classification

| Class | Examples | Handling |
| --- | --- | --- |
| Secret | Passwords, tokens, API keys, certificates | Never logged, never in Git, environment only |
| Identity | ID documents, national id, full IBAN | Never in logs, never in conversation memory, never in telemetry |
| Financial | Balances, transactions, payments | Service layer only; not duplicated into observability |
| Conversational | Messages, summaries, memories | User-owned, user-deletable, expiring |
| Operational | request/run ids, durations, counts, tokens | Freely logged |

### Logging

Structured JSON, correlation ids attached automatically, and a redaction filter
that drops known-sensitive keys (`password`, `token`, `api_key`, `iban`,
`card_number`, `national_id`, `content`, `message`, `answer`, `prompt`, …)
before writing. Log *events* — identifiers, counts, durations, outcomes — not
payloads.

Concrete rule the reference project broke: it stored the full question and
answer of every turn in its metrics table. `AgentRunRecord` deliberately holds
no message content.

### Access logs

The route *template* is logged, never the concrete path: `/accounts/{account_id}`
rather than `/accounts/acc_9f2c…`. Concrete paths carry identifiers.

---

## 4. Configuration and secrets

* No credential exists anywhere in the repository. `.env.example` contains
  placeholders only.
* Only `libra.core.config` reads the environment
  (`test_no_module_reads_the_environment_outside_configuration`), so every
  setting passes validation.
* Deployed environments are refused at startup if development authentication
  is enabled or persistence is in-memory.
* Secrets are supplied by the environment (Azure Key Vault / GitHub Actions
  secrets in CI), never baked into an image.
* `/health` reports deployment *names* and a configured/not-configured flag —
  never endpoints or keys.

---

## 5. Input handling

Pydantic models validate every request body and every tool argument;
`ValidationError` becomes `VALIDATION_ERROR` with field names and no values.
Tool outputs are validated too, so a service change cannot silently feed an
unexpected shape into a prompt.

Uploaded documents (Phase 6) are treated as hostile input: extension and
content-type allow-list, size cap, per-user quota, stored outside the web root
under a generated name, and never executed or rendered inline.

---

## 6. Failure behaviour

Errors fail cleanly and observably. There is **no automatic provider
fallback**: if Foundry is unavailable the request returns
`AI_PROVIDER_UNAVAILABLE`. Silently answering from a different model with
different behaviour and different safety properties would be worse than
failing, and it is guarded by
`test_no_provider_fallback_infrastructure_exists`.

Internal errors return a generic message. Stack traces, driver errors and
identifiers stay in the logs, reachable through the `request_id` the user was
given.

---

## 7. Audit

`audit_events` is append-only and never edited by application code. Every
sensitive operation records who, what, when, from which request, and the
outcome. `agent_runs` and `tool_invocations` provide the AI half: which agent,
which prompt version, which capabilities were used and why they were selected.

Internal execution traces are visible to admins through the observability
dashboard and are never returned to a banking user
(`test_assistant_endpoint_reports_unavailable_without_internals`).

---

## 8. Still to build

Phase 1 and later, tracked in the roadmap:

* password hashing (Argon2id), login, refresh-token rotation, session
  revocation, replacing the development principal resolver;
* rate limiting and brute-force protection on authentication;
* multi-factor authentication for high-risk operations;
* CSRF protection for cookie-based sessions, if cookies are adopted;
* field-level encryption for KYC documents;
* automated dependency and container scanning in CI;
* a documented GDPR erasure workflow (banking records retained under
  obligation; conversation state, memories, documents and chunks removed).
