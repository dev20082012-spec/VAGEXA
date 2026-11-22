import hashlib
import hmac
import ipaddress
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vagexa.adapters.persistence.audit import append_audit
from vagexa.adapters.persistence.models import (
    AuditEvent,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)
from vagexa.adapters.persistence.models import (
    Session as DbSession,
)
from vagexa.api.errors import Problem
from vagexa.domain.passwords import hash_password, verify_password

SESSION_HOURS = 12
LOGIN_WINDOW = timedelta(minutes=15)
LOGIN_LIMIT = 10


@dataclass
class Principal:
    id: uuid.UUID
    username: str
    display_name: str
    roles: list[str]
    session_id: uuid.UUID | None = None
    permissions: frozenset[str] = frozenset()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _roles_for(db: Session, user_id: uuid.UUID) -> list[str]:
    rows = db.execute(
        select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user_id)
    ).scalars()
    return list(rows)


def _permissions_for(db: Session, user_id: uuid.UUID) -> frozenset[str]:
    rows = db.execute(
        select(Permission.name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user_id)
    ).scalars()
    return frozenset(rows)


def _new_session(db: Session, user: User, user_agent: str | None, client_ip: str | None) -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    stored_ip = None
    if client_ip:
        try:
            stored_ip = str(ipaddress.ip_address(client_ip))
        except ValueError:
            stored_ip = None
    db.add(
        DbSession(
            user_id=user.id,
            token_hash=_token_hash(token),
            csrf_token_hash=_token_hash(csrf),
            expires_at=datetime.now(UTC) + timedelta(hours=SESSION_HOURS),
            user_agent=(user_agent or "")[:256] or None,
            client_ip=stored_ip,
        )
    )
    return token, csrf


def login(
    db: Session,
    *,
    username: str,
    password: str,
    request_id: str | None,
    user_agent: str | None,
    client_ip: str | None,
    presented_token: str | None = None,
) -> tuple[str, str, Principal]:
    recent_failures = db.scalar(
        select(func.count())
        .select_from(AuditEvent)
        .where(
            AuditEvent.action == "auth.login_failed",
            AuditEvent.occurred_at >= datetime.now(UTC) - LOGIN_WINDOW,
            AuditEvent.detail["username"].as_string() == username,
        )
    )
    if recent_failures is not None and recent_failures >= LOGIN_LIMIT:
        raise Problem(429, "rate-limited", "Too many attempts", "Try again later.")

    user = db.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(user.password_hash, password):
        append_audit(
            db,
            action="auth.login_failed",
            outcome="failure",
            object_kind="user",
            request_id=request_id,
            detail={"username": username},
        )
        db.commit()
        raise Problem(401, "unauthenticated", "Sign-in failed", "The username or password is incorrect.")
    if user.status != "active":
        raise Problem(403, "forbidden", "Account disabled", "This account cannot sign in.")

    if presented_token:
        previous = db.scalar(select(DbSession).where(DbSession.token_hash == _token_hash(presented_token)))
        if previous is not None and previous.revoked_at is None:
            previous.revoked_at = datetime.now(UTC)
    token, csrf = _new_session(db, user, user_agent, client_ip)
    db.flush()
    session_row = db.scalar(select(DbSession).where(DbSession.token_hash == _token_hash(token)))
    append_audit(
        db,
        action="auth.login",
        outcome="success",
        object_kind="user",
        actor_id=user.id,
        object_id=str(user.id),
        request_id=request_id,
    )
    principal = Principal(
        user.id,
        user.username,
        user.display_name,
        _roles_for(db, user.id),
        session_row.id if session_row else None,
        _permissions_for(db, user.id),
    )
    return token, csrf, principal


def principal_from_token(db: Session, token: str) -> Principal | None:
    row = db.scalar(select(DbSession).where(DbSession.token_hash == _token_hash(token)))
    if row is None or row.revoked_at is not None or row.expires_at <= datetime.now(UTC):
        return None
    user = db.get(User, row.user_id)
    if user is None or user.status != "active":
        return None
    return Principal(
        user.id,
        user.username,
        user.display_name,
        _roles_for(db, user.id),
        row.id,
        _permissions_for(db, user.id),
    )


def issue_csrf(db: Session, principal: Principal) -> str:
    if principal.session_id is None:
        raise Problem(401, "unauthenticated", "Sign-in required", "Sign in to continue.")
    row = db.get(DbSession, principal.session_id)
    if row is None or row.revoked_at is not None:
        raise Problem(401, "unauthenticated", "Sign-in required", "Sign in to continue.")
    csrf = secrets.token_urlsafe(32)
    row.csrf_token_hash = _token_hash(csrf)
    return csrf


def csrf_matches(db: Session, token: str, presented_csrf: str | None) -> bool:
    row = db.scalar(select(DbSession).where(DbSession.token_hash == _token_hash(token)))
    if row is None or row.revoked_at is not None or not row.csrf_token_hash or not presented_csrf:
        return False
    return hmac.compare_digest(row.csrf_token_hash, _token_hash(presented_csrf))


def change_password(
    db: Session,
    *,
    principal: Principal,
    current_password: str,
    new_password: str,
    request_id: str | None,
) -> tuple[str, str]:
    user = db.get(User, principal.id)
    if user is None or not verify_password(user.password_hash, current_password):
        raise Problem(401, "unauthenticated", "Sign-in failed", "The username or password is incorrect.")
    user.password_hash = hash_password(new_password)
    now = datetime.now(UTC)
    others = db.scalars(select(DbSession).where(DbSession.user_id == user.id, DbSession.revoked_at.is_(None)))
    for row in others:
        row.revoked_at = now
    token, csrf = _new_session(db, user, None, None)
    append_audit(
        db,
        action="auth.password_change",
        outcome="success",
        object_kind="user",
        actor_id=user.id,
        object_id=str(user.id),
        request_id=request_id,
    )
    return token, csrf


def set_account_status(
    db: Session,
    *,
    actor: Principal,
    user_id: uuid.UUID,
    status: str,
    request_id: str | None,
) -> None:
    if "users.manage" not in actor.permissions:
        raise Problem(403, "forbidden", "Not allowed", "You cannot change account status.")
    user = db.get(User, user_id)
    if user is None:
        raise Problem(404, "not-found", "Not available", "This user is not available.")
    user.status = status
    if status == "disabled":
        now = datetime.now(UTC)
        for row in db.scalars(
            select(DbSession).where(DbSession.user_id == user.id, DbSession.revoked_at.is_(None))
        ):
            row.revoked_at = now
    append_audit(
        db,
        action="auth.account_status",
        outcome="success",
        object_kind="user",
        actor_id=actor.id,
        object_id=str(user.id),
        request_id=request_id,
        detail={"status": status},
    )


def logout(db: Session, token: str, request_id: str | None) -> None:
    row = db.scalar(select(DbSession).where(DbSession.token_hash == _token_hash(token)))
    if row is None or row.revoked_at is not None:
        return
    row.revoked_at = datetime.now(UTC)
    append_audit(
        db,
        action="auth.logout",
        outcome="success",
        object_kind="session",
        actor_id=row.user_id,
        object_id=str(row.id),
        request_id=request_id,
    )


def create_user(
    db: Session,
    *,
    username: str,
    display_name: str,
    password: str,
    role_names: list[str],
) -> User:
    if db.scalar(select(User).where(User.username == username)) is not None:
        raise Problem(409, "conflict", "Username already exists", "Choose a different username.")
    roles = list(db.scalars(select(Role).where(Role.name.in_(role_names))))
    if len(roles) != len(set(role_names)):
        raise Problem(422, "invalid", "Unknown role", "One or more roles are not recognised.")
    user = User(
        username=username,
        display_name=display_name,
        password_hash=hash_password(password),
        status="active",
    )
    db.add(user)
    db.flush()
    for role in roles:
        db.add(UserRole(user_id=user.id, role_id=role.id))
    return user
