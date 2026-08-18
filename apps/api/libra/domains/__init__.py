"""Deterministic banking domains.

Everything authoritative about money lives here: balances, transactions,
payments, savings, settlements, scores. These modules must never import
``libra.ai`` — banking correctness cannot depend on a model's output.
"""
