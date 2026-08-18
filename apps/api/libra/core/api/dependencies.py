"""FastAPI dependencies.

Authentication note: Phase 0 ships a *development* principal resolver that
reads ``Authorization: Bearer dev:<user_id>:<role>``. It exists so the
authorization boundary is real and testable from day one, and it is refused
outside local/test by :func:`libra.core.config.load_settings`. Phase 1
replaces :func:`get_principal` with JWT verification; no call site changes,
because everything downstream already depends on ``Principal``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Request

from libra.core.config import Settings
from libra.core.container import Container
from libra.core.errors import AuthenticationRequiredError, InvalidCredentialsError
from libra.core.locale import Locale, negotiate
from libra.core.request_context import set_user_id
from libra.core.security.permissions import permissions_for
from libra.core.security.principal import Principal, Role

_DEV_SCHEME = "dev:"


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_locale(accept_language: Annotated[str | None, Header()] = None) -> Locale:
    return negotiate(accept_language)


def get_principal(
    request: Request,
    locale: Annotated[Locale, Depends(get_locale)],
    authorization: Annotated[str | None, Header()] = None,
) -> Principal:
    """Resolve the authenticated caller or refuse the request."""
    settings: Settings = request.app.state.container.settings

    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthenticationRequiredError()

    token = authorization[7:].strip()

    if settings.security.dev_auth_enabled and token.startswith(_DEV_SCHEME):
        principal = _dev_principal(token, locale)
        set_user_id(principal.user_id)
        return principal

    # Phase 1: verify a signed access token here and build the principal from
    # its claims. Until then, no other token format is accepted.
    raise InvalidCredentialsError()


def _dev_principal(token: str, locale: Locale) -> Principal:
    parts = token[len(_DEV_SCHEME) :].split(":")
    if not parts or not parts[0]:
        raise InvalidCredentialsError()

    user_id = parts[0]
    try:
        role = Role(parts[1]) if len(parts) > 1 and parts[1] else Role.CUSTOMER
    except ValueError as error:
        raise InvalidCredentialsError() from error

    return Principal(
        user_id=user_id,
        role=role,
        permissions=frozenset(permissions_for(role)),
        locale=locale,
    )


PrincipalDep = Annotated[Principal, Depends(get_principal)]
ContainerDep = Annotated[Container, Depends(get_container)]
LocaleDep = Annotated[Locale, Depends(get_locale)]
