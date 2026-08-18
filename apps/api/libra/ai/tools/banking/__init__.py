"""Concrete banking tools.

Each module here builds one :class:`~libra.ai.tools.contract.ToolDefinition`
from an application service. Tools contain no business logic of their own —
they translate typed arguments into a service call and the service result into
a typed output. Adding a tool must never add a second implementation of a
banking rule.
"""
