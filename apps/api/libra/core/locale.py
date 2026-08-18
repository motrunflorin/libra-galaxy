"""Locale handling.

Romanian and English are first-class. Business logic stays language
independent: services return stable identifiers (``account_type``,
``category_id``, ``error.code``) and the presentation layer translates them.
Only user-facing AI text is generated in the requested language.
"""

from __future__ import annotations

from enum import Enum


class Locale(str, Enum):
    RO = "ro"
    EN = "en"


DEFAULT_LOCALE = Locale.RO
SUPPORTED_LOCALES = (Locale.RO, Locale.EN)


def negotiate(requested: str | None, *, default: Locale = DEFAULT_LOCALE) -> Locale:
    """Resolve a locale from a header or user preference.

    Accepts ``ro``, ``en``, ``ro-RO``, ``en-GB`` and simple ``Accept-Language``
    lists. Unknown values fall back to ``default`` rather than failing.
    """
    if not requested:
        return default

    for part in requested.split(","):
        tag = part.split(";")[0].strip().lower()
        if not tag:
            continue
        primary = tag.split("-")[0]
        for locale in SUPPORTED_LOCALES:
            if primary == locale.value:
                return locale

    return default
