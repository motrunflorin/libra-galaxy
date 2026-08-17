# Libra Galaxy — Project Context

## 1. Project Overview

**Libra Galaxy** is a bilingual Romanian/English AI-native digital banking web application.

The application is primarily designed for desktop browsers but must provide a fully responsive and usable experience on mobile browsers.

The visual identity is inspired by:

- space
- stars
- planets
- galaxies
- orbital systems

The visual theme must remain elegant and modern without compromising:

- usability
- accessibility
- clarity
- banking trust
- readability

Libra Galaxy is not intended to be only a banking dashboard with an attached chatbot.

The long-term vision is:

> A modular digital banking platform where deterministic banking services and specialized AI agents cooperate through a controlled orchestration layer.

---

# 2. Team

The project is developed by a team of five members.

Four members have strong Computer Science backgrounds.

At least one member has strong frontend and database experience.

The architecture must allow:

- clear module ownership
- parallel development
- independent feature development
- low coupling between modules
- easy onboarding of new contributors
- future extraction of modules into services if necessary

The project should initially remain a **modular monolith**.

Do not introduce microservices without a concrete technical or organizational reason.

---

# 3. Languages

The application must support:

- Romanian
- English

Localization must be part of the architecture from the beginning.

Business logic must remain language-independent.

Use stable identifiers internally and translate presentation text through localization resources.

Financial values must remain numerically exact regardless of locale formatting.

---

# 4. Target Platforms

Primary:

- desktop browser

Required:

- mobile browser
- responsive layouts

The frontend should provide an SPA-like experience.

A native mobile application is not part of the initial scope.

---

# 5. Initial Technology Stack

## Frontend

- Next.js
- React
- TypeScript
- responsive design
- reusable component architecture
- localization
- typed API client

## Backend

- Python
- FastAPI
- REST APIs
- WebSockets only where persistent bidirectional communication provides clear value

FastAPI is the canonical backend.

Next.js server functionality may be used as a thin frontend/BFF layer when useful, but must not duplicate banking business logic.

## AI Platform

Microsoft Foundry.

Initial model capabilities:

```text
General AI / agent reasoning
→ GPT-5 mini

Embeddings
→ text-embedding-3-small

Voice
→ Microsoft/Azure voice capability, exact service/model TBD
```

Model deployment names must be configuration values.

Do not scatter hard-coded model identifiers throughout the application.

## Data

MongoDB is the initial primary database candidate.

All persistence access must be abstracted through repositories.

The architecture must permit additional data stores later if required.

In particular, a future real banking ledger may require a datastore with stronger transactional guarantees.

## Infrastructure

Initial infrastructure direction:

- Docker
- GitHub
- Azure
- Microsoft Foundry
- CI/CD

Infrastructure must initially remain simple.

---

# 6. Important AI Boundary

The AI layer is **not the banking source of truth**.

Structured banking state must come from deterministic application services.

Examples:

```text
"What is my current balance?"
→ AccountService

"How much did I spend last week?"
→ TransactionService

"What subscriptions do I currently pay?"
→ SubscriptionService / Transaction Intelligence pipeline
```

Not:

```text
RAG
LLM memory
conversation summary
model guess
```

Agents may:

- analyze
- classify
- explain
- recommend
- simulate
- retrieve information
- prepare actions
- initiate controlled workflows

Agents must not independently:

- modify account balances
- bypass authorization
- execute arbitrary payments
- modify permissions
- directly manipulate database collections
- make unrestricted compliance decisions
- treat generated content as authoritative banking state

Sensitive actions must flow through deterministic application services.

---

# 7. Initial Banking Domains

The architecture should prepare clear modules for:

## Users

- user profile
- preferences
- locale
- user settings

## Authentication and Authorization

- authentication
- sessions/tokens
- roles
- permissions
- resource ownership

## Accounts

- accounts
- balances
- account details

## Subaccounts

Purpose-oriented money spaces such as:

- Emergency Fund
- Vacation
- Bills
- Investments
- Personal Goals

## Transactions

- transaction history
- transaction metadata
- categories
- merchant normalization
- search/filtering

## Payments

- transfer preparation
- transfer validation
- payment history
- controlled execution workflows

## Payment Groups

- group expenses
- members
- shared payments
- requests
- balances between participants
- settlement calculation

## Savings

- goals
- progress
- target amounts
- target dates

## Allocation Rules

Example:

```text
WHEN salary_received:

10% → Emergency Fund
5%  → Vacation
5%  → Investment Goal
```

AI may recommend allocation rules.

A deterministic Rules Engine must execute them.

## Subscriptions

- recurring transaction detection
- subscription detection
- duplicate subscription detection
- potentially forgotten subscriptions
- user review
- cancellation workflow only where technically supported

## Financial Health

- health score
- score components
- historical snapshots
- spending indicators
- savings indicators
- cash-flow indicators

## Documents

- account statements
- exports
- user documents
- document metadata
- document processing

## KYC / Compliance

Future functionality may include:

- document ingestion
- OCR
- field extraction
- proof-of-address processing
- ID processing
- consistency checks
- missing-information detection
- workflow assistance

Generic vision-model infrastructure is **not part of the current MVP architecture**.

KYC should initially be designed around document/OCR processing abstractions.

## Notifications

- system notifications
- transaction notifications
- proactive AI suggestions
- user-configurable preferences

## Admin

- user administration
- AI observability
- system metrics
- agent runs
- model usage
- operational monitoring

---

# 8. Initial Agent Architecture

Do not create one giant banking agent.

Libra Galaxy should begin with five specialized agent domains.

The orchestrator is infrastructure and should not become an unrestricted sixth domain agent.

---

# 9. Financial Advisor Agent

Responsibilities:

- financial health explanation
- spending insights
- savings recommendations
- financial goal analysis
- budget analysis
- cash-flow explanations
- scenario interpretation
- what-if analysis
- understandable financial explanations

Example:

```text
User:
"What happens if I save 500 RON every month?"
```

Possible flow:

```text
Financial Advisor
        ↓
GetFinancialStateTool
        ↓
ScenarioSimulationTool
        ↓
GoalAnalysisTool
        ↓
Generate explanation
```

The mathematical simulation should be deterministic whenever possible.

The LLM explains the result.

---

# 10. Transaction Intelligence Agent

Responsibilities:

- transaction categorization
- merchant normalization
- recurring transaction detection
- subscription detection
- duplicate subscription detection
- potentially forgotten subscription detection
- spending pattern analysis
- transaction-level explanations

Examples of merchant normalization:

```text
NETFLIX.COM
NETFLIX 1234
Netflix Amsterdam
```

may map to one logical merchant.

This agent should be a strong candidate for the first fully implemented agent because its outputs are measurable and testable.

---

# 11. Compliance / KYC Agent

Responsibilities may later include:

- document workflow assistance
- OCR-result interpretation
- structured field consistency checks
- missing document detection
- missing field detection
- KYC workflow assistance

The agent must not become the sole final decision-maker for high-risk compliance operations.

Deterministic rules and/or human review must remain possible.

Generic multimodal/vision-agent infrastructure is currently out of scope.

---

# 12. Document Intelligence Agent

Responsibilities:

- document ingestion
- account statement explanation
- natural-language document queries
- intelligent exports
- financial document summaries
- RAG over banking documentation
- cited retrieval from relevant knowledge
- user-facing explanations

This area should reuse and improve engineering patterns learned from the Technical Interviewer reference project.

---

# 13. Engagement / Proactive Agent

Responsibilities:

- proactive financial insights
- savings nudges
- notification generation
- achievements
- gamification
- contextual user assistance
- mood-aware communication style
- coordination with voice interaction

Mood-aware behavior may affect:

- tone
- verbosity
- presentation
- notification intensity

Mood must not independently determine:

- financial permissions
- risk
- compliance
- account operations
- objectively calculated financial recommendations

---

# 14. Orchestrator

The orchestration layer coordinates AI execution.

Expected responsibilities:

```text
request understanding
        ↓
authentication context
        ↓
authorization context
        ↓
intent classification
        ↓
risk classification
        ↓
context construction
        ↓
agent selection
        ↓
tool eligibility
        ↓
tool execution
        ↓
validation
        ↓
response construction
        ↓
telemetry / audit
```

The orchestrator should prefer deterministic routing for obvious tasks.

Use agentic routing only when it adds real value.

---

# 15. Tool Architecture

Agents must access application capabilities through typed tools.

Example:

```text
Agent
 ↓
Typed Tool
 ↓
Application Service
 ↓
Repository
 ↓
Database
```

Never:

```text
Agent
 ↓
MongoDB collection
```

Each tool should eventually expose metadata such as:

```text
name
description
input schema
output schema
allowed agents
required permissions
risk level
side effects
requires confirmation
```

Example tools:

```text
GetAccountsTool
GetTransactionsTool
GetSpendingSummaryTool
CategorizeTransactionTool
DetectSubscriptionsTool
GetFinancialHealthTool
CreateSavingsSimulationTool
SearchBankKnowledgeTool
AnalyzeDocumentTool
PrepareTransferTool
CreateNotificationTool
```

---

# 16. Multi-Step Tool Execution

Libra Galaxy should improve upon the Technical Interviewer reference project by supporting explicit multi-step workflows where useful.

Example:

```text
User asks a financial what-if question
        ↓
retrieve relevant structured financial state
        ↓
run deterministic scenario
        ↓
compare against goals
        ↓
generate explanation
```

Execution state should remain structured and observable.

Do not rely on hidden free-form model reasoning as workflow state.

---

# 17. Parallel Tool Execution

Independent read-only tools may execute concurrently.

Example:

```text
Financial Advisor
   ├── GetIncomeHistoryTool
   ├── GetSpendingSummaryTool
   ├── GetSavingsGoalsTool
   └── GetSubscriptionsTool
```

Financial mutations must never be performed speculatively.

---

# 18. RAG

RAG is intended for **unstructured knowledge**.

Examples:

- policies
- procedures
- FAQs
- product documentation
- financial education
- user-uploaded documents
- internal documentation where appropriate

RAG must not be used as the source of truth for:

- balances
- account ownership
- transaction totals
- payment state
- permissions
- current financial ledger state

---

# 19. RAG Pipeline

The initial architecture should support:

```text
document ingestion
      ↓
normalization
      ↓
metadata extraction
      ↓
chunking
      ↓
embedding generation
      ↓
vector storage
      ↓
retrieval
      ↓
ranking
      ↓
context injection
      ↓
source attribution
```

Important document metadata may include:

```text
document_id
source
document_type
language
version
section
checksum
valid_from
valid_until
embedding_model
embedding_version
```

---

# 20. Chunking

Do not use one universal chunking strategy for every document.

Provide a configurable chunking abstraction.

Potential strategies:

```text
FixedWindowChunker
SectionChunker
SemanticChunker
StructuredDocumentChunker
StatementChunker
```

Technical Interviewer's configurable word-based chunking may be used as a baseline pattern, not blindly copied.

Chunk overlap should remain configurable.

---

# 21. Embeddings

Initial embedding model:

```text
text-embedding-3-small
```

Use a dedicated embedding abstraction.

Example:

```text
EmbeddingProvider
    └── MicrosoftFoundryEmbeddingProvider
```

Embedding cache should include enough information to avoid accidental reuse across incompatible embedding configurations.

Useful metadata:

```text
content_hash
embedding_provider
embedding_model
embedding_version
created_at
```

---

# 22. Embedding Cache

Reuse the Technical Interviewer pattern.

Support:

- document embedding cache
- query embedding cache
- reuse of unchanged embeddings

---

# 23. Incremental Re-indexing

Reuse and improve the reference project's pattern.

Expected concept:

```text
document
 ↓
checksum/version
 ↓
compare existing version
 ↓
unchanged
 └→ reuse existing chunks/embeddings

changed
 └→ regenerate affected chunks
     update index
     remove stale chunks
```

Do not regenerate the entire knowledge base after every document change.

---

# 24. Retrieval

Support configurable:

- top-k
- minimum relevance score
- metadata filtering
- language filtering

Do not assume one global threshold is optimal for all document types.

Retrieval tuning should eventually be based on evaluation datasets.

Potential later improvements:

```text
semantic retrieval
+
keyword retrieval
+
metadata filtering
+
reranking
```

---

# 25. Conversation Context

Reuse the strong Technical Interviewer context architecture.

Maintain explicit layers:

```text
recent conversation
        +
conversation summary
        +
relevant historical memories
        +
durable preferences
        +
retrieved knowledge
        +
structured banking context
```

These sources must remain distinguishable.

---

# 26. Memory

Conversation memory must not become financial state.

Example:

```text
"What savings goal did we discuss?"
→ memory

"What is the current amount in my savings account?"
→ AccountService
```

Support context compression so conversation history does not grow indefinitely.

Cross-session memory may later retain appropriate user preferences and useful conversational context.

---

# 27. CashPlay / What-If Lab

CashPlay is a sandbox financial simulation environment.

Examples:

```text
What if I start a 200 RON/month gym membership?

What if I save 500 RON/month?

What if I invest a fixed amount monthly?

What if my rent increases by 10%?

What if I cancel Netflix and Spotify?

What if I buy a 5,000 RON laptop?
```

The workflow should be:

```text
Current financial state
        ↓
Scenario Engine
        ↓
Projected financial state
        ↓
Financial Advisor
        ↓
Explanation
```

CashPlay must never silently modify real account state.

---

# 28. Split Payments and Groups

Support concepts such as:

```text
PaymentGroup
├── members
├── shared expenses
├── contribution history
├── balances
├── money requests
└── settlement suggestions
```

The system may calculate an efficient settlement plan.

AI can explain the result but deterministic logic should calculate monetary balances.

---

# 29. Financial Health Score

Financial Health should eventually combine deterministic indicators such as:

- spending stability
- saving rate
- recurring commitments
- emergency savings
- income/expense balance
- budget adherence

The AI agent may explain:

- why the score changed
- which components influenced it
- possible improvements

The score itself should not be an arbitrary LLM-generated number.

---

# 30. Subscription Intelligence

The system should support:

- recurring payment recognition
- subscription detection
- merchant normalization
- duplicate subscription detection
- potentially forgotten subscriptions

Possible user flow:

```text
subscription detected
        ↓
AI explanation
        ↓
user review
        ↓
supported cancellation mechanism if available
        ↓
explicit confirmation
```

AI must not claim it cancelled something unless the corresponding deterministic operation succeeded.

---

# 31. Voice

Voice should be treated as an interaction channel, not as another domain agent.

Concept:

```text
Voice input
     ↓
speech processing
     ↓
Orchestrator
     ↓
Agent / Tool execution
     ↓
response
     ↓
voice output
```

Exact Microsoft voice technology is intentionally TBD.

Do not prematurely bind the entire architecture to one voice implementation.

---

# 32. API Response Contract

Success:

```json
{
  "success": true,
  "message": "Operation completed successfully.",
  "body": {}
}
```

Failure:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message.",
    "details": null
  }
}
```

When useful:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid operation."
  },
  "request_id": "req_..."
}
```

Use proper HTTP status codes independently from the envelope.

---

# 33. Authentication and Multi-User Support

Unlike the Technical Interviewer reference project, proper multi-user support is mandatory.

The architecture must support:

```text
user
authentication
authorization
roles
permissions
resource ownership
session ownership
admin permissions
audit events
```

Every sensitive resource must enforce server-side access control.

Never rely on frontend-only authorization.

---

# 34. Persistence Architecture

Application logic should not depend directly on MongoDB-specific APIs.

Prefer:

```text
Router
 ↓
Service
 ↓
Repository Interface
 ↓
MongoDB Repository
```

Example:

```text
AccountRepository
TransactionRepository
PaymentRepository
UserRepository
ConversationRepository
DocumentRepository
```

This allows future persistence changes without rewriting application logic.

---

# 35. Observability

Preserve one of the strongest engineering ideas from Technical Interviewer.

Track AI execution metadata such as:

```text
request_id
user_id
session_id
agent
tool
model deployment
prompt version
latency
token usage
estimated cost
retrieval activity
errors
```

Potential metrics:

- model latency
- time to first token
- tool latency
- database latency
- retrieval latency
- tool error rate
- retrieval success
- token consumption
- estimated AI cost

Sensitive banking information must not be unnecessarily logged.

---

# 36. AI Observability Dashboard

The Admin area should eventually provide internal visibility into:

```text
agent runs
model usage
token usage
estimated cost
tool calls
tool latency
retrieval activity
errors
prompt versions
agent versions
```

Internal execution traces must not be exposed to regular banking users.

---

# 37. Error Handling

The system should distinguish errors such as:

```text
validation error
authentication error
authorization error
database error
AI provider error
tool timeout
retrieval error
agent execution error
external service error
voice service error
```

Errors should fail cleanly and observably.

There is currently **no automatic alternate-provider fallback architecture**.

If a required AI service is unavailable, the operation should fail safely and produce an observable error.

---

# 38. Provider Architecture

Use provider abstractions for modularity.

Initially:

```text
ChatProvider
    └── MicrosoftFoundryChatProvider

EmbeddingProvider
    └── MicrosoftFoundryEmbeddingProvider

VoiceProvider
    └── MicrosoftVoiceProvider
```

The purpose of these interfaces is maintainability and replacement capability.

Do not implement automatic provider fallback at this stage.

---

# 39. Current Explicit Non-Goals

The initial architecture should NOT prioritize:

- microservices
- Kubernetes
- multiple AI-provider fallback
- local Ollama fallback
- generic vision-model infrastructure
- native mobile application
- complex automatic model routing
- unrestricted autonomous financial agents
- complete production banking ledger infrastructure
- unnecessary distributed systems
- speculative abstractions with no current use case

---

# 40. Engineering Reference Project

A separate repository exists at:

```text
/home/regelepirat/AI-Academy/technical-interviewer-chatbot
```

It is an engineering reference only.

Engineering feedback is stored in:

```text
docs/reference/technical-interviewer/ENGINEERING_FEEDBACK.md
```

Strong patterns worth studying include:

- modular architecture
- context assembly
- conversation history
- context compression
- cross-session memory
- RAG
- chunking
- retrieval
- embeddings
- embedding cache
- incremental indexing
- provider abstraction
- tool registries
- parallel tool execution
- session management
- structured logging
- token tracking
- cost tracking
- performance metrics
- observability dashboard

Areas Libra Galaxy should improve include:

- real authentication
- multi-user isolation
- authorization
- tool permissions
- controlled orchestration
- multi-step tool workflows
- document governance
- banking-state separation
- auditability

Do not transfer:

- interview prompts
- CV logic
- candidate logic
- interview procedures
- interview-specific tools
- interview-specific business logic
- CLI-specific features unless independently useful

---

# 41. Development Philosophy

Prefer:

```text
simple
→ correct
→ tested
→ observable
→ modular
→ scalable
```

over:

```text
complex
→ impressive-looking
→ difficult to maintain
```

The objective of the first architecture phase is not to build every feature.

The objective is to create a small, correct, scalable foundation on which the team can safely build Libra Galaxy.