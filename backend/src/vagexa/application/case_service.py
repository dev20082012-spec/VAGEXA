import hashlib
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from vagexa.adapters.persistence.audit import append_audit
from vagexa.adapters.persistence.models import Case, CaseAssignment, SyntheticBatch
from vagexa.api.errors import Problem
from vagexa.application.auth_service import Principal
from vagexa.domain.authorization import case_role_allows
from vagexa.domain.classification import ClassificationRejected, assert_case_classification

_MANUAL_GROUND_TRUTH = hashlib.sha256(b"vagexa-manual-case").hexdigest()


def _assignment(db: Session, user_id: uuid.UUID, case_id: uuid.UUID) -> CaseAssignment | None:
    return db.get(CaseAssignment, (case_id, user_id))


def list_cases(db: Session, principal: Principal) -> list[Case]:
    return list(
        db.scalars(
            select(Case)
            .join(CaseAssignment, CaseAssignment.case_id == Case.id)
            .where(CaseAssignment.user_id == principal.id)
            .where(CaseAssignment.case_role.in_(["lead", "investigator", "analyst", "auditor"]))
            .order_by(Case.created_at.desc())
        )
    )


def get_case(db: Session, principal: Principal, case_id: uuid.UUID, request_id: str | None) -> Case:
    case = db.get(Case, case_id)
    assignment = _assignment(db, principal.id, case_id)
    if case is None or assignment is None or not case_role_allows(assignment.case_role, "cases.read"):
        append_audit(
            db,
            action="case.open",
            outcome="denied",
            object_kind="case",
            actor_id=principal.id,
            object_id=str(case_id),
            request_id=request_id,
        )
        raise Problem(404, "not-found", "Not available", "This case is not available.")
    append_audit(
        db,
        action="case.open",
        outcome="success",
        object_kind="case",
        actor_id=principal.id,
        case_id=case.id,
        object_id=str(case.id),
        request_id=request_id,
    )
    return case


def create_case(
    db: Session,
    principal: Principal,
    *,
    reference: str,
    title: str,
    opened_on: date,
    data_classification: str,
    data_mode: str,
    synthetic_batch_id: uuid.UUID | None,
    request_id: str | None,
) -> Case:
    if "cases.create" not in principal.permissions:
        raise Problem(403, "forbidden", "Not allowed", "You cannot open a case.")
    try:
        assert_case_classification(data_mode, data_classification)
    except ClassificationRejected as exc:
        raise Problem(422, "invalid", "Classification refused", str(exc)) from exc

    batch_id = synthetic_batch_id
    if data_classification == "synthetic" and batch_id is None:
        batch = SyntheticBatch(
            scenario_key="investigator-opened",
            generator_version="manual.v1",
            ground_truth_sha256=_MANUAL_GROUND_TRUTH,
        )
        db.add(batch)
        db.flush()
        batch_id = batch.id
    if data_classification == "synthetic" and batch_id is not None:
        if db.get(SyntheticBatch, batch_id) is None:
            raise Problem(422, "invalid", "Unknown synthetic batch", "The synthetic batch does not exist.")

    case = Case(
        reference=reference.strip(),
        title=title.strip(),
        status="open",
        data_classification=data_classification,
        synthetic_batch_id=batch_id,
        opened_on=opened_on,
        created_by=principal.id,
    )
    db.add(case)
    try:
        db.flush()
    except IntegrityError as exc:
        raise Problem(
            409, "conflict", "Reference already used", "That case reference already exists."
        ) from exc
    db.add(
        CaseAssignment(
            case_id=case.id,
            user_id=principal.id,
            case_role="lead",
            assigned_by=principal.id,
        )
    )
    append_audit(
        db,
        action="case.create",
        outcome="success",
        object_kind="case",
        actor_id=principal.id,
        case_id=case.id,
        object_id=str(case.id),
        request_id=request_id,
        detail={"data_classification": data_classification},
    )
    return case


def assign_case(
    db: Session,
    principal: Principal,
    *,
    case_id: uuid.UUID,
    user_id: uuid.UUID,
    case_role: str,
    request_id: str | None,
) -> None:
    if "cases.assign" not in principal.permissions:
        raise Problem(403, "forbidden", "Not allowed", "You cannot assign cases.")
    if case_role not in {"lead", "investigator", "analyst", "auditor"}:
        raise Problem(422, "invalid", "Unknown case role", "That case role is not recognised.")
    if db.get(Case, case_id) is None:
        raise Problem(404, "not-found", "Not available", "This case is not available.")
    if _assignment(db, user_id, case_id) is not None:
        raise Problem(409, "conflict", "Already assigned", "That user is already assigned.")
    db.add(
        CaseAssignment(
            case_id=case_id,
            user_id=user_id,
            case_role=case_role,
            assigned_by=principal.id,
        )
    )
    append_audit(
        db,
        action="assignment.create",
        outcome="success",
        object_kind="case_assignment",
        actor_id=principal.id,
        case_id=case_id,
        object_id=str(user_id),
        request_id=request_id,
        detail={"case_role": case_role},
    )
