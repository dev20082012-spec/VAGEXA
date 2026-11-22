import uuid
from typing import Any

from sqlalchemy.orm import Session

from vagexa.adapters.persistence.models import AuditEvent


def append_audit(
    db: Session,
    *,
    action: str,
    outcome: str,
    object_kind: str,
    actor_id: uuid.UUID | None = None,
    case_id: uuid.UUID | None = None,
    object_id: str | None = None,
    request_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditEvent(
            action=action,
            outcome=outcome,
            object_kind=object_kind,
            actor_id=actor_id,
            case_id=case_id,
            object_id=object_id,
            request_id=request_id,
            detail=detail or {},
        )
    )
