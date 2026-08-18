"""The five domain agent specifications.

These are declarations, not implementations. Phase 3 implements
``transaction_intelligence`` first because its outputs (categories, merchant
keys, detected subscriptions) are measurable against a labelled dataset.

Every ``allowed_tools`` entry must also list the agent in the tool's own
``allowed_agents`` set; ``tests/test_agent_specs.py`` asserts both directions
agree, so a capability cannot be granted from one side only.
"""

from __future__ import annotations

from libra.ai.agents.contract import AgentSpec
from libra.ai.tools.contract import RiskLevel

FINANCIAL_ADVISOR = AgentSpec(
    agent_id="financial_advisor",
    display_name="Financial Advisor",
    purpose="Explain the user's financial situation and the consequences of choices.",
    responsibilities=(
        "Explain financial health scores and what moved them.",
        "Interpret deterministic scenario projections (CashPlay / what-if).",
        "Analyse savings goals, budgets and cash-flow patterns.",
        "Recommend allocation rules for the user to review and approve.",
    ),
    prohibited=(
        "Computing balances, projections or scores itself.",
        "Executing transfers or changing allocation rules.",
        "Presenting a recommendation as a regulated financial advice product.",
    ),
    allowed_tools=frozenset({"get_accounts", "run_scenario"}),
    risk_ceiling=RiskLevel.LOW,
    prompt_version="advisor-v0",
    evaluation=(
        "Numeric fidelity: every figure in the answer must appear in a tool output.",
        "Refusal set: questions requiring an action must end in a confirmation request.",
        "Bilingual quality review on a fixed RO/EN question set.",
    ),
    future_extensions=(
        "Goal feasibility analysis across multiple savings goals.",
        "Budget adherence coaching driven by financial-health components.",
    ),
)

TRANSACTION_INTELLIGENCE = AgentSpec(
    agent_id="transaction_intelligence",
    display_name="Transaction Intelligence",
    purpose="Turn raw transaction descriptors into structured, reviewable meaning.",
    responsibilities=(
        "Categorise transactions the deterministic rules could not classify.",
        "Normalise merchant descriptors into stable merchant keys.",
        "Explain detected recurring payments and possible subscriptions.",
        "Explain spending patterns computed by TransactionService.",
    ),
    prohibited=(
        "Computing spending totals itself.",
        "Marking a subscription cancelled without a successful deterministic operation.",
        "Writing categories directly to storage without the review workflow.",
    ),
    allowed_tools=frozenset({"get_accounts"}),
    risk_ceiling=RiskLevel.LOW,
    prompt_version="transactions-v0",
    evaluation=(
        "Categorisation accuracy against a labelled transaction dataset.",
        "Merchant normalisation precision/recall on descriptor variants.",
        "Subscription detection false-positive rate.",
    ),
    future_extensions=(
        "Duplicate-subscription detection across merchants.",
        "Forgotten-subscription surfacing with user review.",
    ),
)

COMPLIANCE_KYC = AgentSpec(
    agent_id="compliance_kyc",
    display_name="Compliance / KYC",
    purpose="Assist a KYC workflow that a deterministic policy or a human decides.",
    responsibilities=(
        "Interpret OCR output and flag inconsistencies between extracted fields.",
        "Detect missing documents and missing required fields.",
        "Summarise a case for the reviewing officer.",
    ),
    prohibited=(
        "Approving or rejecting a KYC case.",
        "Deciding risk ratings or sanctions outcomes.",
        "Storing identity-document images or full document text in conversation memory.",
    ),
    allowed_tools=frozenset(),
    risk_ceiling=RiskLevel.LOW,
    prompt_version="compliance-v0",
    evaluation=(
        "Every produced flag maps to a deterministic rule identifier.",
        "Human-review handoff is present in 100% of decision-shaped outputs.",
    ),
    future_extensions=("Document-completeness checklists per KYC workflow state.",),
)

DOCUMENT_INTELLIGENCE = AgentSpec(
    agent_id="document_intelligence",
    display_name="Document Intelligence",
    purpose="Answer questions about documents and bank knowledge, with citations.",
    responsibilities=(
        "Answer from retrieved policy, procedure, product and FAQ content.",
        "Explain the structure and entries of an account statement.",
        "Summarise a user-uploaded document the user has access to.",
        "Always attribute answers to the retrieved source.",
    ),
    prohibited=(
        "Answering balance, ownership, payment-state or permission questions from retrieval.",
        "Retrieving another user's documents.",
        "Presenting an unretrieved claim as a cited fact.",
    ),
    allowed_tools=frozenset(),
    risk_ceiling=RiskLevel.LOW,
    prompt_version="documents-v0",
    evaluation=(
        "Citation coverage: every factual sentence maps to a retrieved chunk.",
        "Refusal on out-of-corpus questions instead of guessing.",
        "RO/EN retrieval quality measured separately.",
    ),
    future_extensions=("Statement-specific chunking and cross-statement comparison.",),
)

ENGAGEMENT = AgentSpec(
    agent_id="engagement",
    display_name="Engagement / Proactive",
    purpose="Turn deterministic insights into timely, well-toned nudges.",
    responsibilities=(
        "Phrase notifications for insights produced by deterministic services.",
        "Adapt tone and verbosity to user preferences and locale.",
        "Surface achievements and progress toward savings goals.",
    ),
    prohibited=(
        "Inventing an insight that no service produced.",
        "Letting tone or mood influence financial recommendations, risk or permissions.",
        "Sending notifications the user has disabled.",
    ),
    allowed_tools=frozenset({"get_accounts"}),
    risk_ceiling=RiskLevel.LOW,
    prompt_version="engagement-v0",
    evaluation=(
        "Every notification links to the deterministic insight that triggered it.",
        "Preference compliance: disabled categories are never generated.",
    ),
    future_extensions=("Voice-channel tone adaptation.", "Gamified savings streaks."),
)

ALL_SPECS: tuple[AgentSpec, ...] = (
    FINANCIAL_ADVISOR,
    TRANSACTION_INTELLIGENCE,
    COMPLIANCE_KYC,
    DOCUMENT_INTELLIGENCE,
    ENGAGEMENT,
)
