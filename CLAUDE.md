# Libra Galaxy — Claude Development Instructions

## 1. Authoritative Project Context

Before making architectural or implementation decisions, read:

`PROJECT_CONTEXT.md`

Treat it as the authoritative product specification.

If code and project documentation disagree, identify the discrepancy instead of silently choosing one.

---

## 2. Primary Workspace

Libra Galaxy is the primary project.

All new implementation work must be created inside the Libra Galaxy repository.

Do not create project files outside the repository unless explicitly requested.

---

## 3. External Engineering Reference

A separate repository is available at:

`/home/regelepirat/AI-Academy/technical-interviewer-chatbot`

This repository belongs to a completely different product.

It is **READ-ONLY engineering reference material**.

Never:

- edit it
- delete files from it
- rename files inside it
- move files inside it
- format its source files
- create new files inside it
- commit changes to it

Engineering feedback about this reference project is stored at:

`docs/reference/technical-interviewer/ENGINEERING_FEEDBACK.md`

Before borrowing a pattern from the reference repository:

1. identify the engineering pattern;
2. understand why it exists;
3. inspect the evaluator feedback;
4. identify weaknesses or limitations;
5. determine whether it fits Libra Galaxy;
6. adapt it to banking requirements;
7. implement the improved version only inside Libra Galaxy.

Never blindly copy the reference implementation.

Never introduce interview-domain logic into Libra Galaxy.

---

## 4. Reference Patterns Worth Studying

Useful areas from Technical Interviewer include:

- modular services
- registries
- RAG
- chunking
- embedding abstraction
- embedding cache
- incremental re-indexing
- retrieval
- configurable retrieval thresholds
- conversation history
- session management
- context compression
- cross-session memory
- tool registry
- parallel tool execution
- provider abstraction
- structured logging
- token tracking
- cost estimation
- performance metrics
- observability dashboard

Libra Galaxy should improve the reference implementation where banking requires stronger:

- authentication
- authorization
- user isolation
- tool permissions
- auditability
- multi-step orchestration
- data governance
- transaction safety

---

## 5. Development Workflow

Before implementing a non-trivial feature:

1. inspect the relevant existing code;
2. identify the owning module/domain;
3. identify existing abstractions that should be reused;
4. identify security implications;
5. identify whether AI is actually necessary;
6. propose the smallest appropriate implementation;
7. implement;
8. test;
9. report significant architectural decisions.

Do not perform broad refactors unrelated to the requested task.

Do not generate large amounts of placeholder code.

Do not create abstractions without a concrete use case.

---

## 6. Architectural Style

Start as a **modular monolith**.

Do not introduce microservices merely for architectural appearance.

Maintain clear boundaries so modules may later be extracted if justified.

Prefer explicit dependencies between modules.

Avoid circular dependencies.

---

## 7. Canonical Backend

FastAPI is the canonical application backend.

Preferred flow:

```text
API Router
    ↓
Application Service
    ↓
Repository
    ↓
Persistence
```

Next.js server functionality may act as a thin frontend/BFF layer when useful.

Do not duplicate FastAPI business logic in Next.js.

Never maintain two independent implementations of:

- account logic
- transaction logic
- payments
- authorization
- AI orchestration
- financial calculations

---

## 8. Database Access

Do not access MongoDB directly from:

- API routers
- agents
- prompts
- frontend code

Use repository abstractions.

Preferred:

```text
Router
 ↓
Service
 ↓
Repository Interface
 ↓
MongoDB Implementation
```

For agents:

```text
Agent
 ↓
Typed Tool
 ↓
Service
 ↓
Repository
```

Persistence-specific code must remain isolated.

---

## 9. AI Safety Boundary

LLMs are not authoritative banking systems.

Never allow generated model output alone to:

- change balances
- execute transfers
- modify permissions
- authorize users
- modify account ownership
- directly alter ledger state
- cancel products
- make unrestricted compliance decisions

Sensitive operations must pass through deterministic services.

Where applicable require:

- authentication
- authorization
- validation
- user confirmation
- idempotency
- audit logging

---

## 10. Agent Architecture

Do not create one giant general-purpose banking agent.

Initial domain agents are:

1. Financial Advisor Agent
2. Transaction Intelligence Agent
3. Compliance/KYC Agent
4. Document Intelligence Agent
5. Engagement/Proactive Agent

The orchestrator is infrastructure, not an unrestricted sixth domain agent.

Each agent should eventually have:

- explicit purpose
- responsibilities
- prohibited responsibilities
- allowed tools
- typed inputs
- structured outputs where practical
- risk level
- test scenarios
- evaluation criteria
- prompt/version identifier

Agents should be independently replaceable.

---

## 11. Orchestrator

The orchestration layer should eventually support:

```text
request
 ↓
identity context
 ↓
authorization context
 ↓
intent
 ↓
risk
 ↓
context construction
 ↓
agent selection
 ↓
tool eligibility
 ↓
execution
 ↓
validation
 ↓
response
 ↓
telemetry
```

Prefer deterministic routing for obvious tasks.

Use model-based routing only when it provides clear value.

Do not create a complex autonomous planner in the initial MVP without a concrete requirement.

---

## 12. Tool Design

Agents interact with application functionality through typed tools.

Never allow unrestricted agent database access.

Each tool should eventually describe:

- name
- description
- input schema
- output schema
- allowed agents
- required permissions
- side effects
- risk level
- whether confirmation is required

Read-only tools may often run concurrently.

Mutation tools require stronger controls.

---

## 13. Multi-Step Execution

Libra Galaxy should support explicit multi-step workflows where useful.

Prefer structured workflow state.

Do not use hidden free-form model reasoning as durable application state.

Example:

```text
retrieve financial state
        ↓
run scenario calculation
        ↓
compare goals
        ↓
generate explanation
```

Do not introduce multi-step agent loops when one deterministic service call is sufficient.

---

## 14. Microsoft AI Platform

Use Microsoft Foundry as the initial AI platform.

Initial capabilities:

```text
Chat / reasoning
→ GPT-5 mini

Embeddings
→ text-embedding-3-small

Voice
→ Microsoft/Azure service, exact implementation TBD
```

Deployment names must come from configuration.

Do not scatter model deployment names throughout business logic.

---

## 15. Provider Abstractions

Use provider interfaces where they provide real modularity.

Initial direction:

```text
ChatProvider
    └── MicrosoftFoundryChatProvider

EmbeddingProvider
    └── MicrosoftFoundryEmbeddingProvider

VoiceProvider
    └── MicrosoftVoiceProvider
```

These abstractions exist so implementations can be replaced later.

Do **not** implement automatic provider fallback at this stage.

There is no Azure-to-Ollama or equivalent fallback requirement in the current scope.

If a required AI provider fails, fail safely and observably.

---

## 16. Vision

Generic vision-model infrastructure is currently out of scope.

Do not introduce:

- VisionProvider
- multimodal model routing
- generic image reasoning architecture
- local vision models

KYC/document functionality may later use OCR and document-processing capabilities through a dedicated document-processing abstraction.

Do not introduce vision infrastructure prematurely.

---

## 17. RAG Boundary

RAG is for unstructured information.

Valid examples:

- policies
- procedures
- product information
- FAQs
- financial education
- documents
- account statement explanations

Invalid uses:

```text
current balance
current account ownership
exact transaction total
payment state
permissions
ledger state
```

Those must be obtained through deterministic application services.

---

## 18. RAG Architecture

Reuse the strong ideas from Technical Interviewer but improve them where appropriate.

The pipeline should remain modular:

```text
ingestion
 ↓
normalization
 ↓
metadata
 ↓
chunking
 ↓
embedding
 ↓
indexing
 ↓
retrieval
 ↓
ranking
 ↓
context injection
```

Preserve source information throughout the pipeline.

---

## 19. Chunking

Do not apply one chunk size blindly to every document.

Create strategy-based chunking when justified.

Potential strategies:

- fixed window
- section-aware
- semantic
- structured document
- statement-specific

Chunk overlap must remain configurable.

Do not copy Technical Interviewer's exact chunk parameters unless evaluation demonstrates they are appropriate.

---

## 20. Retrieval

Retrieval settings should be configurable.

Support concepts such as:

- top-k
- minimum score
- metadata filters
- language filters

Do not assume one threshold is optimal for every corpus.

Prefer evaluation-driven tuning.

---

## 21. Embeddings

Use a dedicated embedding provider.

Initial model:

`text-embedding-3-small`

Preserve embedding cache and incremental indexing patterns from the reference project.

Embedding records should contain enough metadata to prevent reuse across incompatible models or versions.

---

## 22. Incremental Indexing

Do not rebuild the entire vector index when only one document changes.

Prefer:

```text
content hash
→ compare existing version
→ reuse unchanged chunks
→ regenerate changed chunks
→ remove stale chunks
```

Keep indexing independently testable.

---

## 23. Context Builder

Do not allow every agent to assemble context arbitrarily.

Prefer a central context-building abstraction.

Possible context sections:

```text
identity
permissions
locale
recent conversation
conversation summary
relevant memories
retrieved knowledge
structured banking context
tool results
execution metadata
```

Keep context sources logically separate.

---

## 24. Memory

Separate:

1. recent conversation
2. compact conversation summary
3. durable user preferences
4. retrieved historical memory
5. authoritative banking state

Never treat conversational memory as authoritative banking state.

Example:

```text
"What did we discuss about my vacation savings?"
→ memory

"How much money is currently in my vacation account?"
→ banking service
```

Context compression is encouraged to control token usage.

---

## 25. Deterministic Computation

Do not use an LLM where normal code is safer and simpler.

Examples that should normally remain deterministic:

- balances
- arithmetic
- percentages
- settlement calculations
- savings projections
- rule execution
- permission checks
- financial-health formula components

The LLM may explain these results.

---

## 26. Authentication and Authorization

Libra Galaxy is a multi-user application.

Server-side authorization is mandatory.

Always consider:

- authenticated user
- ownership
- role
- permission
- resource access

Never rely on frontend-only security.

---

## 27. API Contract

Successful responses should follow:

```json
{
  "success": true,
  "message": "...",
  "body": {}
}
```

Failed responses should follow:

```json
{
  "success": false,
  "error": {
    "code": "...",
    "message": "...",
    "details": null
  }
}
```

Use proper HTTP status codes.

Prefer stable machine-readable error codes.

Use request IDs for traceable failures where appropriate.

---

## 28. Frontend

Use:

- Next.js
- React
- TypeScript

Design responsive layouts from the beginning.

Prefer feature-oriented frontend modules.

Keep:

- reusable UI components
- typed contracts
- centralized API access
- localization
- loading states
- error states
- empty states
- accessibility

The AI assistant is one part of the banking product, not the entire interface.

---

## 29. Localization

Romanian and English are first-class languages.

Do not duplicate application logic for each language.

Use translation resources.

Persist stable internal identifiers instead of translated labels where possible.

---

## 30. Voice

Treat voice as an input/output channel.

Do not create a "Voice Agent" solely because voice exists.

Voice should use the same orchestrator and domain agents as text interactions.

The exact Microsoft voice implementation is currently undecided.

Keep this area replaceable and isolated.

---

## 31. KYC

KYC is an important future domain.

Current architecture may prepare module boundaries but should not overbuild it now.

Initial relevant abstractions may include:

- document ingestion
- OCR service
- extracted fields
- validation
- workflow status

Do not implement generic vision infrastructure.

Final sensitive KYC decisions must remain controllable by deterministic policies and/or human review.

---

## 32. Observability

Preserve the strong observability ideas from Technical Interviewer.

Track useful metadata such as:

- request ID
- user ID where safe
- session ID
- agent
- tool
- model deployment
- prompt version
- latency
- token usage
- estimated cost
- retrieval metrics
- errors

Never unnecessarily log:

- passwords
- access tokens
- secrets
- complete identity documents
- sensitive banking payloads

---

## 33. Structured Logging

Prefer structured logs.

Use trace/request identifiers.

Make logs useful for debugging across:

```text
frontend request
→ API
→ orchestrator
→ agent
→ tool
→ service
→ database
```

---

## 34. Token and Cost Tracking

Track AI usage from the beginning where practical.

Useful dimensions:

```text
feature
agent
model deployment
session
environment
```

Do not sacrifice correctness or security purely to reduce model cost.

---

## 35. Testing

Every significant implementation should include appropriate tests.

Prioritize:

- service tests
- repository tests
- API contract tests
- authentication tests
- authorization tests
- tool tests
- deterministic financial calculation tests
- retrieval tests
- agent evaluation scenarios

When fixing a failing test:

do not change the expectation merely to make the implementation pass unless the previous expectation is demonstrably incorrect.

---

## 36. Code Quality

Prefer:

- clear names
- typing
- small focused modules
- explicit interfaces
- minimal duplication
- dependency injection where useful
- testable services

Avoid:

- giant utility modules
- giant service classes
- giant agents
- business logic in routers
- business logic in prompts
- global mutable state
- unnecessary patterns or factories

---

## 37. Security

Never commit:

- secrets
- API keys
- database passwords
- Foundry credentials
- private certificates
- access tokens

Use configuration/environment variables.

Validate all external input.

Apply authorization server-side.

Treat uploaded documents and banking data as sensitive.

---

## 38. Current Explicit Non-Goals

Do not introduce unless explicitly requested:

- microservices
- Kubernetes
- automatic AI-provider fallback
- Ollama/local fallback
- generic vision infrastructure
- native mobile application
- overly complex model routing
- fully autonomous financial actions
- speculative distributed infrastructure

Keep the initial architecture minimal.

---

## 39. Architecture Changes

Before making a significant structural change:

1. explain the current design;
2. identify the problem;
3. propose the change;
4. explain the tradeoff;
5. implement only after the change is justified.

Record major decisions in architecture documentation when appropriate.

Do not create an ADR for every small implementation detail.

---

## 40. Documentation

Keep documentation useful and concise.

Initial important documents may include:

```text
README.md
PROJECT_CONTEXT.md
CLAUDE.md
ARCHITECTURE.md
AGENTS.md
API_CONVENTIONS.md
DATABASE.md
AI_ARCHITECTURE.md
SECURITY.md
```

Do not create all documents immediately if they would only contain placeholders.

Create them as the architecture becomes concrete.

---

## 41. First Project Phase

The first task is **architecture design**, not full implementation.

Before generating application code:

1. inspect `PROJECT_CONTEXT.md`;
2. inspect this `CLAUDE.md`;
3. inspect `docs/reference/technical-interviewer/ENGINEERING_FEEDBACK.md`;
4. inspect the Technical Interviewer reference repository;
5. identify reusable engineering patterns;
6. identify patterns that should not be transferred;
7. propose the minimum scalable Libra Galaxy architecture;
8. propose the repository structure;
9. propose implementation phases;
10. identify what the five team members can develop in parallel.

Do not create the complete application until the architecture proposal has been reviewed.