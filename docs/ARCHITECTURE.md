# Architecture

Libra Galaxy is a **modular monolith with strong domain boundaries**, deployed
as two processes: a FastAPI backend (the canonical application) and a Next.js
frontend (a thin UI/BFF layer).

Microservices are deliberately not used. Five developers on one product do not
have a distribution problem — they have a *boundary* problem, and boundaries
are cheaper to enforce inside one deployable. The layout below keeps every
module extractable later if a real reason appears.

---

## 1. Layers

```text
┌──────────────────────────────────────────────────────────────┐
│  apps/web — Next.js                                          │
│  routing, i18n, feature UI, typed API client                 │
│  no banking rules, no direct database access                 │
└───────────────────────────┬──────────────────────────────────┘
                            │ HTTPS, response envelope
┌───────────────────────────▼──────────────────────────────────┐
│  libra.api — routers                                         │
│  request/response models, dependency injection               │
└───────────────────────────┬──────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
┌───────▼─────────────────┐          ┌──────────▼───────────────┐
│  libra.ai               │  tools   │  libra.domains           │
│  orchestrator, agents,  │─────────▶│  accounts, transactions, │
│  tools, context, memory │          │  payments, savings,      │
│  RAG, telemetry         │          │  scenarios, …            │
└───────┬─────────────────┘          └──────────┬───────────────┘
        │                                       │
        └───────────────────┬───────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────┐
│  libra.core                                                  │
│  config, errors, money, locale, security, persistence,       │
│  HTTP envelope, logging, request context                     │
└───────────────────────────┬──────────────────────────────────┘
                            │
                    ┌───────▼────────┐
                    │  MongoDB       │
                    └────────────────┘
```

### Dependency rules

| Rule | Why | Enforced by |
| --- | --- | --- |
| `domains` must not import `ai` | Balances stay correct with the AI layer removed | `test_banking_domains_do_not_depend_on_the_ai_layer` |
| `core` must not import `domains` or `ai` | Keeps the platform reusable and cycle-free | `test_core_depends_on_no_higher_layer` |
| `ai.agents` / `ai.orchestration` must not import `domains` | Agents reach banking only through typed tools | `test_agents_never_reach_into_banking_domains_directly` |
| Only `core.persistence.mongo` and `*_repository` may import a Mongo driver | No agent, tool or router touches collections | `test_only_repositories_and_the_mongo_provider_import_a_database_driver` |
| Routers must not import repositories | Authorization lives in services, so routers cannot skip it | `test_routers_do_not_import_repositories` |
| Only `core.config` may read the environment | Every setting passes validation | `test_no_module_reads_the_environment_outside_configuration` |
| No module-level service singletons | Testability and per-environment wiring | `test_no_module_level_service_singletons` |

These are executable rules, not conventions: `apps/api/tests/test_architecture_boundaries.py`
parses every module's imports and fails the build with the offending file.

The one deliberate exception is `libra.core.container` — the composition root.
It knows the whole graph because building the graph is its job.

---

## 2. Request lifecycle

```text
HTTP request
  → RequestContextMiddleware      assign request_id, bind to context vars
  → dependency: get_principal     authenticate → Principal (user, role, permissions)
  → router                        validate input, no logic
  → application service           authorize (permission + ownership), apply rules
  → repository interface          user-scoped query
  → MongoDB repository            documents, BSON, indexes
  ← domain objects
  ← success envelope + request_id
```

Failures follow the same path in reverse: a service raises a `LibraError`
subclass, the registered exception handler renders the failure envelope with a
stable code and the correct HTTP status. Unexpected exceptions become a generic
`INTERNAL_ERROR` — stack traces and driver messages never reach a client.

---

## 3. Banking domains

Each domain owns its models, repository contract and application service.
Cross-domain access always goes service → service, never repository →
repository.

| Domain | Owns | Depends on | Status |
| --- | --- | --- | --- |
| `identity` | users, roles, preferences, locale | — | scaffolded |
| `accounts` | accounts, subaccounts, balances | identity | scaffolded |
| `transactions` | history, categories, merchant keys, spending aggregation | accounts | scaffolded |
| `scenarios` | CashPlay projections (pure engine) | — | implemented |
| `payments` | transfer preparation, execution, idempotency | accounts | planned |
| `groups` | payment groups, shared expenses, settlement | payments, accounts | planned |
| `savings` | goals, progress, allocation rules engine | accounts, transactions | planned |
| `subscriptions` | recurring detection, review, cancellation workflow | transactions | planned |
| `financial_health` | indicators, score components, snapshots | transactions, savings | planned |
| `documents` | uploads, statements, exports, metadata | identity | planned |
| `compliance` | KYC workflow, OCR results, human review | documents, identity | planned |
| `notifications` | delivery, preferences, proactive insights | — | planned |
| `admin` | user administration, AI observability | all (read-only) | planned |

*Scaffolded* means models, repository interface, service and tests exist for
the paths the foundation needs. *Planned* means the boundary is designed here
and in `DATABASE.md`, but no placeholder code was created — empty modules cost
review time and hide real progress.

### Money

Every amount is a `Money` value: an integer count of minor units plus a
currency. Floating point never touches a balance. `Money.allocate()` splits an
amount across weights without losing or inventing a single ban, which is the
basis of split-payment settlement.

---

## 4. The AI layer

`libra.ai` is a *consumer* of the banking domains, never a peer.

```text
Orchestrator (infrastructure — never answers anything itself)
  ├── IntentClassifier      deterministic RO/EN rules
  ├── RiskClassifier        risk from intent, not from wording
  ├── AgentRouter           intent → agent lookup table
  ├── ContextBuilder        one assembler, per-source budgets, provenance
  ├── ToolRegistry          typed tools with declared permissions and risk
  ├── ToolExecutor          parallel reads, sequential mutations, timeouts
  └── TelemetryRecorder     agent runs, tool invocations, tokens, cost
```

Details live in [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) and
[AGENTS.md](AGENTS.md).

---

## 5. Frontend

Next.js is a presentation layer. It formats, translates and orchestrates
navigation; it does not decide whether a transfer is allowed or what a balance
is.

```text
apps/web/src/
  app/[locale]/     routes, locale-scoped
  features/<name>/  feature modules: api.ts + components
  lib/api/          the single typed client (envelope, errors, request ids)
  i18n/             ro.json / en.json + negotiation
```

The rule "never duplicate FastAPI business logic in Next.js" is a review
checklist item: a feature module may call endpoints and format results, and
must not recompute a total, a score or an eligibility rule.

---

## 6. Persistence

Application logic depends on repository interfaces. MongoDB is an
implementation detail behind them.

Four state families are kept separate (see [DATABASE.md](DATABASE.md)):

1. authoritative banking state,
2. AI/conversation state,
3. document and RAG state,
4. audit and observability state.

They are separate because they have different truth guarantees, different
retention rules and different access controls. Mixing them is how a
conversation summary ends up being treated as a balance.

A future real ledger may need stronger transactional guarantees than MongoDB.
That is a repository-level change: services depend on `AccountRepository`, not
on Motor.

---

## 7. Observability

Every request carries a `request_id` from the frontend through the API,
orchestrator, agent, tool, service and repository into every log line
(`libra.core.request_context`). Logs are structured JSON with a redaction
filter that drops known-sensitive keys before writing.

AI execution is recorded as `AgentRunRecord` / `ToolInvocationRecord` /
`UsageRecord`: identifiers, counts, durations, tokens and cost — never message
content. See [SECURITY.md](SECURITY.md) for what must never be logged.

---

## 8. What was deliberately left out

Microservices, Kubernetes, provider fallback, local model fallback, generic
vision infrastructure, a model-based planner, native mobile. Each is an
explicit non-goal in `PROJECT_CONTEXT.md`, and two of them are guarded by
tests (`test_no_provider_fallback_infrastructure_exists`,
`test_no_generic_vision_infrastructure_exists`) so they cannot reappear by
accident.
