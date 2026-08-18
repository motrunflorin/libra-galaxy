# Libra Galaxy

A bilingual (Romanian/English) AI-native digital banking web application:
deterministic banking services and specialised AI agents cooperating through a
controlled orchestration layer.

> **Status: Phase 0 — architecture and foundation.**
> The architecture is designed, documented and materialised. Banking features,
> authentication and the agents themselves are implemented in later phases —
> see [`docs/DEVELOPMENT_ROADMAP.md`](docs/DEVELOPMENT_ROADMAP.md).

---

## The one rule that shapes everything

**An LLM is not a banking system.** Every number a user sees comes from a
deterministic service; the AI may explain it, never produce it. Every
state-changing operation runs through an application service with
authentication, authorization, validation and an audit trail.

```text
Agent → Typed Tool → Application Service → Repository → MongoDB
```

There is no other path. `tests/test_architecture_boundaries.py` fails the
build if one is introduced.

---

## Repository layout

```text
apps/
  api/            FastAPI backend — the canonical application (Python)
    libra/
      core/       config, errors, money, security, persistence, HTTP envelope
      domains/    deterministic banking domains (authoritative state)
      ai/         orchestrator, agents, tools, context, memory, RAG, telemetry
      api/        HTTP routers
    knowledge/    registered RAG corpus (registry.json + documents)
    tests/        service, contract, boundary and architecture tests
  web/            Next.js frontend (TypeScript) — thin UI/BFF layer
docs/             architecture, AI, agents, database, API, security, roadmap
infra/docker/     Dockerfiles and the local development stack
```

---

## Getting started

```bash
# backend
cd apps/api
pip install -e ".[dev]"
python -m pytest                     # 135 tests, no database or credentials needed
python -m libra.main serve --reload  # http://127.0.0.1:8000/docs

# RAG pipeline dry-run (no provider calls, no cost)
python -m libra.main knowledge-plan

# frontend
cd apps/web && npm install && npm run dev

# full stack
docker compose -f infra/docker/docker-compose.yml up --build
```

Copy `.env.example` to `.env` and fill in your own values. The repository
contains no credentials, and the API refuses to start in a deployed
environment with development authentication or in-memory persistence enabled.

Common tasks are also available through `make help`.

### Calling the API in development

Phase 0 ships a development principal resolver so the authorization boundary
is real and testable before the Phase 1 login flow exists:

```bash
curl -H "Authorization: Bearer dev:usr_alice:customer" \
     -H "Accept-Language: ro" \
     http://127.0.0.1:8000/api/v1/accounts
```

This scheme is rejected outside `local`/`test`.

---

## Documentation

| Document | What it covers |
| --- | --- |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Layers, domains, dependency rules, request lifecycle |
| [AI_ARCHITECTURE.md](docs/AI_ARCHITECTURE.md) | Orchestrator, context, memory, RAG, providers, observability |
| [AGENTS.md](docs/AGENTS.md) | The five agents: scope, tools, risk, evaluation |
| [DATABASE.md](docs/DATABASE.md) | Collections, ownership, indexes, lifecycle |
| [API_CONVENTIONS.md](docs/API_CONVENTIONS.md) | Envelope, error codes, versioning, pagination |
| [SECURITY.md](docs/SECURITY.md) | AuthN/AuthZ, isolation, AI safety boundary, data handling |
| [DEVELOPMENT_ROADMAP.md](docs/DEVELOPMENT_ROADMAP.md) | Phases and the five-person parallel plan |
| [decisions/](docs/decisions/) | Architecture decision records |
| [reference/technical-interviewer/](docs/reference/technical-interviewer/) | What was reused from the reference project, and what was not |

`PROJECT_CONTEXT.md` is the authoritative product specification and
`CLAUDE.md` the engineering instructions; both take precedence over the
documents above.
