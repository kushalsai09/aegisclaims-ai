from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Any, cast
from urllib.parse import urlencode

import httpx
import jwt

from insurance_platform.ports.identity import IdentityError


@dataclass(frozen=True, slots=True)
class OIDCLoginMaterial:
    state: str
    nonce: str
    code_verifier: str
    code_challenge: str
    browser_binding: str


@dataclass(frozen=True, slots=True)
class ExternalOIDCIdentity:
    subject: str
    email: str
    display_name: str


def login_material() -> OIDCLoginMaterial:
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    )
    return OIDCLoginMaterial(state, nonce, verifier, challenge, secrets.token_urlsafe(32))


def opaque_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class OIDCAuthorizationCodeClient:
    """Provider-neutral OIDC authorization-code + PKCE client."""

    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        client_id: str,
        client_secret: str,
        scopes: str,
        timeout_seconds: float = 5.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._issuer = issuer.rstrip("/")
        self._audience = audience
        self._client_id = client_id
        self._client_secret = client_secret
        self._scopes = scopes
        self._client = httpx.Client(timeout=timeout_seconds, transport=transport)

    def authorization_url(
        self, *, state: str, nonce: str, code_challenge: str, redirect_uri: str
    ) -> str:
        metadata = self._metadata()
        endpoint = self._https_endpoint(metadata, "authorization_endpoint")
        return f"{endpoint}?{
            urlencode(
                {
                    'response_type': 'code',
                    'client_id': self._client_id,
                    'redirect_uri': redirect_uri,
                    'scope': self._scopes,
                    'state': state,
                    'nonce': nonce,
                    'code_challenge': code_challenge,
                    'code_challenge_method': 'S256',
                }
            )
        }"

    def exchange(
        self, *, code: str, code_verifier: str, redirect_uri: str, expected_nonce_hash: str
    ) -> ExternalOIDCIdentity:
        try:
            metadata = self._metadata()
            token_endpoint = self._https_endpoint(metadata, "token_endpoint")
            jwks_uri = self._https_endpoint(metadata, "jwks_uri")
            response = self._client.post(
                token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "code_verifier": code_verifier,
                },
            )
            response.raise_for_status()
            token_payload = response.json()
            id_token = token_payload.get("id_token")
            if not isinstance(id_token, str):
                raise IdentityError("OIDC provider response did not contain an ID token")
            jwks_response = self._client.get(jwks_uri)
            jwks_response.raise_for_status()
            header = jwt.get_unverified_header(id_token)
            key_id = header.get("kid")
            jwks = jwks_response.json().get("keys", [])
            jwk = next(
                (item for item in jwks if isinstance(item, dict) and item.get("kid") == key_id),
                None,
            )
            if jwk is None:
                raise IdentityError("OIDC token signing key is unavailable")
            claims = jwt.decode(
                id_token,
                jwt.PyJWK.from_dict(jwk).key,
                algorithms=["RS256", "ES256"],
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
        except IdentityError:
            raise
        except (httpx.HTTPError, ValueError, jwt.PyJWTError) as exc:
            raise IdentityError("OIDC provider validation failed") from exc

        nonce = claims.get("nonce")
        if not isinstance(nonce, str) or not hmac.compare_digest(
            opaque_hash(nonce), expected_nonce_hash
        ):
            raise IdentityError("OIDC nonce validation failed")
        subject = claims.get("sub")
        email = claims.get("email")
        if not isinstance(subject, str) or not isinstance(email, str):
            raise IdentityError("OIDC identity is missing required claims")
        display_name = claims.get("name")
        return ExternalOIDCIdentity(
            subject=subject,
            email=email.lower(),
            display_name=display_name if isinstance(display_name, str) else email,
        )

    def _metadata(self) -> dict[str, Any]:
        try:
            response = self._client.get(f"{self._issuer}/.well-known/openid-configuration")
            response.raise_for_status()
            metadata = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise IdentityError("OIDC discovery failed") from exc
        if metadata.get("issuer") != self._issuer:
            raise IdentityError("OIDC discovery issuer mismatch")
        return cast(dict[str, Any], metadata)

    @staticmethod
    def _https_endpoint(metadata: dict[str, Any], name: str) -> str:
        endpoint = metadata.get(name)
        if not isinstance(endpoint, str) or not endpoint.startswith("https://"):
            raise IdentityError(f"OIDC discovery contains an invalid {name}")
        return endpoint
