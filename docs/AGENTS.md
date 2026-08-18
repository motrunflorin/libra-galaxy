# Agents

Five bounded specialists. The orchestrator is infrastructure, not a sixth
general-purpose agent.

Each agent is declared as data in `apps/api/libra/ai/agents/specs.py` — purpose,
responsibilities, prohibitions, allowed tools, risk ceiling, prompt version,
evaluation strategy. The specification is executable documentation: the
orchestrator, the eligibility checks and the admin dashboard all read the same
object, so this document cannot drift from behaviour.

---

## Rules that apply to every agent

1. **Reads banking state only through typed tools.** No repository, no
   collection, no direct service import.
2. **Never produces a financial figure.** It explains figures that a
   deterministic service computed.
3. **Cannot exceed its declared tool set.** Checked before execution
   (eligibility) and after (`Orchestrator._validate`).
4. **Cannot escalate its own permissions.** The `Principal` is passed through
   unchanged; privileges only narrow.
5. **Never claims an action succeeded** unless the deterministic operation
   returned success.
6. **Answers in the user's locale**, with identical numbers in both languages.
7. **Is independently replaceable.** Agents never call each other.

A capability must be granted from **both** sides — the agent lists the tool and
the tool lists the agent. `test_agent_specs_and_tool_grants_agree` fails
otherwise, so a one-sided grant cannot ship.

---

## 1. Financial Advisor — `financial_advisor`

| | |
| --- | --- |
| **Purpose** | Explain the user's financial situation and the consequences of choices |
| **Tools** | `get_accounts`, `run_scenario` |
| **Risk ceiling** | LOW |
| **Prompt version** | `advisor-v0` |
| **Intents routed here** | account overview, what-if, financial advice |

**Responsibilities** — explain financial health scores and what moved them;
interpret deterministic scenario projections; analyse savings goals, budgets
and cash flow; recommend allocation rules for the user to approve.

**Prohibited** — computing balances, projections or scores itself; executing
transfers or changing allocation rules; presenting recommendations as a
regulated financial advice product.

**Evaluation** — numeric fidelity (every figure in the answer must appear in a
tool output); refusal set (action requests must end in a confirmation request);
bilingual quality review on a fixed RO/EN question set.

**Typical flow**

```text
"What if I save 500 RON every month?"
  → get_accounts            (authoritative opening balance)
  → run_scenario            (deterministic 12-month projection)
  → get_savings_goals       (planned)
  → explanation in RO/EN, citing the projection
```

---

## 2. Transaction Intelligence — `transaction_intelligence`

| | |
| --- | --- |
| **Purpose** | Turn raw transaction descriptors into structured, reviewable meaning |
| **Tools** | `get_accounts` (+ transaction tools in Phase 3) |
| **Risk ceiling** | LOW |
| **Prompt version** | `transactions-v0` |
| **Intents routed here** | spending analysis, subscription review |

**Responsibilities** — categorise transactions deterministic rules could not
classify; normalise merchant descriptors (`NETFLIX.COM`, `NETFLIX 1234`,
`Netflix Amsterdam` → `netflix`); explain detected recurring payments and
possible subscriptions; explain spending patterns computed by
`TransactionService`.

**Prohibited** — computing spending totals itself; marking a subscription
cancelled without a successful deterministic operation; writing categories
straight to storage without the review workflow.

**Evaluation** — categorisation accuracy against a labelled dataset; merchant
normalisation precision/recall on descriptor variants; subscription-detection
false-positive rate.

> **First agent to implement (Phase 3).** Its outputs are discrete and
> measurable, so it can be evaluated against ground truth rather than judged by
> impression — which is exactly what a team needs from its first agent.

---

## 3. Compliance / KYC — `compliance_kyc`

| | |
| --- | --- |
| **Purpose** | Assist a KYC workflow that a deterministic policy or a human decides |
| **Tools** | none yet |
| **Risk ceiling** | LOW |
| **Prompt version** | `compliance-v0` |
| **Intents routed here** | KYC workflow |

**Responsibilities** — interpret OCR output and flag inconsistencies between
extracted fields; detect missing documents and fields; summarise a case for the
reviewing officer.

**Prohibited** — approving or rejecting a case; deciding risk ratings or
sanctions outcomes; storing identity-document images or full document text in
conversation memory.

**Evaluation** — every flag maps to a deterministic rule identifier; a
human-review handoff is present in 100% of decision-shaped outputs.

No generic vision infrastructure: document understanding goes through a
dedicated OCR/document-processing abstraction (Phase 6).

---

## 4. Document Intelligence — `document_intelligence`

| | |
| --- | --- |
| **Purpose** | Answer questions about documents and bank knowledge, with citations |
| **Tools** | retrieval tools (Phase 4) |
| **Risk ceiling** | LOW |
| **Prompt version** | `documents-v0` |
| **Intents routed here** | document question, knowledge question, **unknown** |

**Responsibilities** — answer from retrieved policy, procedure, product and FAQ
content; explain the structure of an account statement; summarise a document
the user owns; always attribute answers to the retrieved source.

**Prohibited** — answering balance, ownership, payment-state or permission
questions from retrieval; retrieving another user's documents; presenting an
unretrieved claim as a cited fact.

**Evaluation** — citation coverage (every factual sentence maps to a retrieved
chunk); refusal on out-of-corpus questions instead of guessing; RO and EN
retrieval quality measured separately.

Unclassified intents route here deliberately: the agent that must cite a source
for everything is the safest default.

---

## 5. Engagement / Proactive — `engagement`

| | |
| --- | --- |
| **Purpose** | Turn deterministic insights into timely, well-toned nudges |
| **Tools** | `get_accounts` |
| **Risk ceiling** | LOW |
| **Prompt version** | `engagement-v0` |

**Responsibilities** — phrase notifications for insights produced by
deterministic services; adapt tone and verbosity to preferences and locale;
surface achievements and savings-goal progress.

**Prohibited** — inventing an insight no service produced; letting tone or mood
influence financial recommendations, risk or permissions; sending notifications
the user disabled.

**Evaluation** — every notification links to the deterministic insight that
triggered it; preference compliance (disabled categories are never generated).

Mood affects *how* something is said. It never affects what is true, what is
permitted or what is recommended.

---

## Agent evaluation

Evaluations live beside the agent they test and run in CI as a separate suite
from unit tests (they are slower and need a provider):

```text
apps/api/tests/evaluations/<agent_id>/
  dataset.jsonl          input + expected properties
  test_<agent_id>.py     assertions over the properties
```

Four assertion families, in decreasing order of confidence:

1. **Structural** — output schema, citation presence, refusal shape. Exact.
2. **Numeric fidelity** — every number in the answer appears in a tool output.
   Exact, and the single most valuable check for a banking assistant.
3. **Behavioural** — tool selection, confirmation requests, permission
   refusals. Exact.
4. **Quality** — bilingual clarity, tone. Human-reviewed on a fixed set.

An agent version ships when 1–3 pass at 100% on the regression set. Prompt
versions are recorded on every run, so a regression can be attributed to a
specific prompt revision.

---

## Adding an agent

1. Add an `AgentSpec` to `specs.py` — purpose, responsibilities, **prohibited**,
   allowed tools, risk ceiling, prompt version, evaluation strategy.
2. Add the agent id to `allowed_agents` on every tool it needs.
3. Map its intents in `ai/orchestration/routing.py`.
4. Implement `Agent.handle()` and register it in the container.
5. Add the evaluation dataset and tests.

If a new capability needs a new tool, the tool comes first — with its schemas,
permissions, side effect and risk level — and only then the agent that uses it.
