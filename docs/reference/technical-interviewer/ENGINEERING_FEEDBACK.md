# Technical Interviewer — Engineering Feedback Scope Adjustment

For the initial Libra Galaxy architecture, **fallback providers and vision-model infrastructure are intentionally out of scope**.

## Remove from the reference analysis

Do not transfer or design the following Technical Interviewer patterns at this stage:

* Azure → Ollama chat fallback
* Azure → Ollama embedding fallback
* local-model fallback infrastructure
* fallback routing
* fallback metrics
* fallback reasons
* generic vision model abstraction
* Ollama vision integration
* vision-specific context injection
* automatic failover between AI providers

These may be reconsidered later if the project requires them.

---

## AI stack for the current MVP

The initial Libra Galaxy AI stack should assume:

```text
Microsoft Foundry
│
├── GPT-5 mini
│
├── text-embedding-3-small
│
└── Microsoft/Azure voice service
```

Provider abstractions should still exist so that models can be replaced later, but **automatic fallback behavior should not be implemented now**.

Example:

```text
ChatProvider
    └── MicrosoftFoundryChatProvider

EmbeddingProvider
    └── MicrosoftFoundryEmbeddingProvider

VoiceProvider
    └── MicrosoftVoiceProvider
```

The abstractions exist for modularity, not for fallback.

---

## Multiple Models

The useful lesson from Technical Interviewer is the separation of models according to task.

For Libra Galaxy, initially:

```text
Chat / reasoning
→ GPT-5 mini

Embeddings
→ text-embedding-3-small

Voice
→ dedicated Microsoft voice capability
```

Do not introduce a generic `VisionModel` abstraction at this stage.

---

## Model Selection

The first implementation should use explicit capability-based routing.

Example:

```text
general agent reasoning
→ GPT-5 mini

financial explanation
→ GPT-5 mini

transaction categorization requiring LLM
→ GPT-5 mini

RAG embeddings
→ text-embedding-3-small

voice input/output
→ Microsoft voice service
```

Avoid building a sophisticated automatic model router in the MVP.

The architecture should make future routing possible without requiring it now.

---

## Robust Error Handling

Keep robust error handling for:

* Microsoft Foundry calls
* embeddings
* retrieval
* tools
* database operations
* external APIs
* voice services
* agent execution

Expected categories include:

```text
validation error
authentication error
authorization error
AI provider error
tool timeout
database failure
external service failure
agent failure
retrieval failure
voice service failure
```

If the configured AI provider is unavailable, the operation should currently **fail cleanly and observably** rather than automatically switching to another provider.

---

## Cost Optimization

Keep:

* embedding cache
* query embedding cache
* context compression
* prompt/context limits
* incremental indexing
* deterministic computation when LLM use is unnecessary
* appropriate model usage
* retrieval limits

Remove fallback-to-local-models as a cost optimization strategy.

---

## Technical Interviewer Patterns to Preserve

The following remain valuable:

1. Modular architecture.
2. Registries.
3. Provider abstractions.
4. Dynamic context construction.
5. Conversation history.
6. Context compression.
7. Cross-session memory concepts.
8. Configurable chunking.
9. Retrieval.
10. Retrieval thresholds.
11. Dedicated embedding model.
12. Embedding cache.
13. Incremental re-indexing.
14. Tool registry.
15. Parallel execution of safe tools.
16. Structured logging.
17. Performance metrics.
18. Token tracking.
19. Cost tracking.
20. Session management.
21. AI observability dashboard.
22. Multi-step tool workflows, improved for Libra Galaxy.

---

## Current Libra Galaxy Scope

The architecture should therefore evolve approximately as:

```text
                    LIBRA GALAXY

                         User
                           │
                           ▼
                      Next.js UI
                           │
                           ▼
                        FastAPI
                           │
                           ▼
                    Orchestrator
                           │
          ┌────────────────┼────────────────┐
          │                │                │
        Agents           Tools          Context
          │                │                │
          ▼                ▼                ▼
      GPT-5 mini       Services         Memory/RAG
                           │                │
                           ▼                ▼
                       MongoDB       embeddings
                                     
                                text-embedding-3-small
```

Voice will be added as another interaction channel using Microsoft services.

Vision infrastructure and provider fallback infrastructure are deliberately deferred.
