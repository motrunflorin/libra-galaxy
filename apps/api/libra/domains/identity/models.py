"""Identity domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from libra.core.locale import DEFAULT_LOCALE, Locale
from libra.core.security.principal import Role


@dataclass(frozen=True)
class UserPreferences:
    """Durable, user-set preferences. Not conversation memory."""

    locale: Locale = DEFAULT_LOCALE
    currency: str = "RON"
    notifications_enabled: bool = True
    proactive_insights_enabled: bool = True


@dataclass(frozen=True)
class User:
    user_id: str
    email: str
    display_name: str
    role: Role = Role.CUSTOMER
    status: str = "active"
    preferences: UserPreferences = field(default_factory=UserPreferences)
    created_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.status == "active"
