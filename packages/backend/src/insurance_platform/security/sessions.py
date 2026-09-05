from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from insurance_platform.infrastructure.models import UserModel, UserSessionModel
from insurance_platform.ports.identity import IdentityError

PASSWORD_MAX_LENGTH = 256
EMAIL_MAX_LENGTH = 254
_password_hasher = PasswordHasher()


@dataclass(frozen=True, slots=True)
class IssuedSession:
    token: str
    expires_at: datetime
    user: UserModel


class DisabledAccountError(IdentityError):
    pass


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


class LocalAccountSessionService:
    """Database-backed local authentication shaped like a replaceable enterprise boundary."""

    def __init__(
        self,
        session: Session,
        *,
        ttl_seconds: int,
        remember_ttl_seconds: int,
    ) -> None:
        self._session = session
        self._ttl_seconds = ttl_seconds
        self._remember_ttl_seconds = remember_ttl_seconds

    def authenticate(self, email: str, password: str, *, remember: bool) -> IssuedSession:
        normalized_email = email.strip().lower()
        if len(normalized_email) > EMAIL_MAX_LENGTH or len(password) > PASSWORD_MAX_LENGTH:
            raise IdentityError("invalid email or password")
        user = self._session.scalar(
            select(UserModel)
            .where(UserModel.email == normalized_email)
            .options(selectinload(UserModel.roles))
        )
        if (
            user is None
            or not user.password_hash
            or not verify_password(user.password_hash, password)
        ):
            raise IdentityError("invalid email or password")
        if not user.is_active or user.account_status != "active":
            raise DisabledAccountError("This account is disabled. Contact an administrator.")

        return self.issue_for_user(user, remember=remember)

    def issue_for_user(self, user: UserModel, *, remember: bool) -> IssuedSession:
        if not user.is_active or user.account_status != "active":
            raise DisabledAccountError("This account is disabled. Contact an administrator.")
        now = datetime.now(UTC)
        expires_at = now + timedelta(
            seconds=self._remember_ttl_seconds if remember else self._ttl_seconds
        )
        token = secrets.token_urlsafe(32)
        self._session.add(
            UserSessionModel(
                tenant_id=user.tenant_id,
                user_id=user.id,
                token_hash=self._token_hash(token),
                expires_at=expires_at,
                last_seen_at=now,
            )
        )
        user.last_login_at = now
        self._session.commit()
        return IssuedSession(token=token, expires_at=expires_at, user=user)

    def verify(self, token: str) -> UserModel:
        now = datetime.now(UTC)
        record = self._session.scalar(
            select(UserSessionModel)
            .where(UserSessionModel.token_hash == self._token_hash(token))
            .options(selectinload(UserSessionModel.user).selectinload(UserModel.roles))
        )
        if record is None or record.revoked_at is not None or self._expired(record.expires_at, now):
            raise IdentityError("session is invalid or expired")
        if not record.user.is_active or record.user.account_status != "active":
            raise IdentityError("session is invalid or expired")
        record.last_seen_at = now
        self._session.commit()
        return record.user

    def revoke(self, token: str) -> None:
        record = self._session.scalar(
            select(UserSessionModel).where(
                UserSessionModel.token_hash == self._token_hash(token),
                UserSessionModel.revoked_at.is_(None),
            )
        )
        if record is not None:
            record.revoked_at = datetime.now(UTC)
            self._session.commit()

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def _expired(expires_at: datetime, now: datetime) -> bool:
        comparable = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=UTC)
        return comparable <= now
