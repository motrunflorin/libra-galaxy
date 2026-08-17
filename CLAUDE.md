# Libra Galaxy — Claude Development Instructions

## Authoritative context

Read PROJECT_CONTEXT.md before making architectural decisions.

## Primary workspace

Libra Galaxy is the only repository that may be modified.

## External reference repository

The repository:

/home/regelepirat/AI-Academy/technical-interviewer-chatbot

is READ-ONLY engineering reference material.

Never modify this repository.

Engineering feedback about it is located at:

docs/reference/technical-interviewer/ENGINEERING_FEEDBACK.md

When using the reference repository:

1. Identify the engineering pattern.
2. Understand why it exists.
3. Read the corresponding engineering feedback.
4. Determine whether the pattern is appropriate for Libra Galaxy.
5. Improve it where necessary.
6. Implement the adapted solution inside Libra Galaxy only.

Never copy interview-specific business logic into Libra Galaxy.

## Architecture principles

- modular monolith initially
- FastAPI is the canonical backend
- Next.js handles frontend/UI concerns
- agents never directly manipulate banking state
- typed tools between agents and domain services
- RAG is not a source of truth for banking data
- provider abstractions for Foundry models
- modular agents
- auditable tool calls
- testability
- observability
- security by default

...