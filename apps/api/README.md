# Libra Galaxy API

The canonical backend. FastAPI, Python 3.10+.

```bash
pip install -e ".[dev]"
python -m pytest                     # 135 tests, no database or credentials
python -m libra.main serve --reload  # http://127.0.0.1:8000/docs
python -m libra.main knowledge-plan  # RAG dry-run: no provider calls, no cost
python -m libra.main indexes         # apply declared MongoDB indexes
```

## Layout

```text
libra/
  core/         config, errors, money, locale, security, persistence,
                HTTP envelope, logging, request context, container
  domains/      deterministic banking domains — authoritative state
  ai/           orchestrator, agents, tools, context, memory, RAG, telemetry
  api/v1/       routers
knowledge/      registered RAG corpus (registry.json + documents)
tests/          service, contract, boundary and architecture tests
```

Dependencies point downwards only: `api → ai → domains → core`.
`tests/test_architecture_boundaries.py` fails the build if that is violated.

## Working here

* Services take a `Principal` and authorize before they act. Routers do not.
* Repositories are interfaces; only `*_repository.py` may import a Mongo driver.
* Amounts are `Money` (integer minor units). Never a float.
* Only `core/config.py` reads the environment.
* Nothing is constructed at import time — the container wires the graph.
* A new tool ships with its schemas, permissions, side effect and risk level in
  the same commit.

## Local authentication

Phase 0 uses a development principal resolver, refused outside `local`/`test`:

```bash
curl -H "Authorization: Bearer dev:usr_alice:customer" \
     http://127.0.0.1:8000/api/v1/accounts
```

Roles: `customer`, `support`, `compliance_officer`, `admin`, `service`.
