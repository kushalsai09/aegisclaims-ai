from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any
from uuid import UUID

from insurance_platform.ports.identity import IdentityError, VerifiedIdentity


class LocalIdentityProvider:
    """HMAC-signed, short-lived identity tokens for local development only."""

    issuer = "insurance-ops-local-development"

    def __init__(self, secret: str, ttl_seconds: int = 28_800) -> None:
        self._secret = secret.encode()
        self._ttl_seconds = ttl_seconds

    def issue(self, user_id: UUID, tenant_id: UUID, subject: str) -> str:
        payload = {
            "iss": self.issuer,
            "sub": subject,
            "user_id": str(user_id),
            "tenant_id": str(tenant_id),
            "exp": int(time.time()) + self._ttl_seconds,
        }
        encoded = _encode(json.dumps(payload, separators=(",", ":")).encode())
        signature = _encode(hmac.new(self._secret, encoded.encode(), hashlib.sha256).digest())
        return f"{encoded}.{signature}"

    async def verify(self, token: str) -> VerifiedIdentity:
        try:
            encoded, supplied_signature = token.split(".", maxsplit=1)
            expected = _encode(hmac.new(self._secret, encoded.encode(), hashlib.sha256).digest())
            if not hmac.compare_digest(supplied_signature, expected):
                raise IdentityError("invalid local identity signature")
            payload: dict[str, Any] = json.loads(_decode(encoded))
            if payload.get("iss") != self.issuer or int(payload["exp"]) <= int(time.time()):
                raise IdentityError("local identity token is expired or has an invalid issuer")
            return VerifiedIdentity(
                user_id=UUID(payload["user_id"]),
                tenant_id=UUID(payload["tenant_id"]),
                subject=str(payload["sub"]),
            )
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise IdentityError("malformed local identity token") from exc


class OIDCIdentityProvider:
    """Production identity extension point; no enterprise IdP is configured locally."""

    async def verify(self, token: str) -> VerifiedIdentity:
        del token
        raise IdentityError("OIDC verifier is not configured")


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _decode(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding).decode()
