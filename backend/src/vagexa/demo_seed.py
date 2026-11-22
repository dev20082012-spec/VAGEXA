"""Load SYN-DEMO through the normal services. Safe to run again: existing rows are reused.

Usage: python -m vagexa.demo_seed --username investigator
The user must already exist. This command does not create accounts or passwords.
"""

import argparse
import hashlib
import json
import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from vagexa.adapters.persistence.audit import append_audit
from vagexa.adapters.persistence.models import (
    AnalyticalRun,
    Case,
    CaseAssignment,
    DnsObservation,
    DomainName,
    HostingObservation,
    IpAddress,
    SyntheticBatch,
    Transaction,
    User,
)
from vagexa.adapters.persistence.session import init_engine, open_session
from vagexa.application import (
    analysis_service,
    bridge_service,
    case_service,
    correlation_service,
    infrastructure_service,
    ingestion_service,
)
from vagexa.application.auth_service import Principal, _permissions_for, _roles_for
from vagexa.application.correlation_service import correlation_input_hash
from vagexa.config import Settings, load_settings
from vagexa.intelligence.digital.normalise import normalise_domain, normalise_ip
from vagexa.synthetic import demo
from vagexa.synthetic.datasets import IFSC

REQUEST_ID = "demo-seed"


def _principal(db: Session, username: str) -> Principal:
    user = db.scalar(select(User).where(User.username == username))
    if user is None or user.status != "active":
        raise SystemExit(
            f"User {username!r} does not exist or is not active. Create it with vagexa.bootstrap."
        )
    return Principal(
        user.id,
        user.username,
        user.display_name,
        _roles_for(db, user.id),
        None,
        _permissions_for(db, user.id),
    )


def _case(db: Session, settings: Settings, principal: Principal) -> Case:
    case = db.scalar(select(Case).where(Case.reference == demo.REFERENCE))
    if case is None:
        truth = json.dumps(demo.ground_truth(), sort_keys=True).encode()
        batch = SyntheticBatch(
            scenario_key=demo.SCENARIO_KEY,
            generator_version=demo.GENERATOR_VERSION,
            ground_truth_sha256=hashlib.sha256(truth).hexdigest(),
        )
        db.add(batch)
        db.flush()
        case = case_service.create_case(
            db,
            principal,
            reference=demo.REFERENCE,
            title=demo.TITLE,
            opened_on=date.fromisoformat(demo.OPENED_ON),
            data_classification="synthetic",
            data_mode=settings.data_mode,
            synthetic_batch_id=batch.id,
            request_id=REQUEST_ID,
        )
    if db.get(CaseAssignment, (case.id, principal.id)) is None:
        db.add(
            CaseAssignment(case_id=case.id, user_id=principal.id, case_role="lead", assigned_by=principal.id)
        )
        db.flush()
    if case.title != demo.TITLE:
        case.title = demo.TITLE
        append_audit(
            db,
            action="case.retitle",
            outcome="success",
            object_kind="case",
            actor_id=principal.id,
            case_id=case.id,
            object_id=str(case.id),
            request_id=REQUEST_ID,
            detail={"generator_version": demo.GENERATOR_VERSION},
        )
    if case.synthetic_batch_id is not None:
        stored = db.get(SyntheticBatch, case.synthetic_batch_id)
        truth = json.dumps(demo.ground_truth(), sort_keys=True).encode()
        digest = hashlib.sha256(truth).hexdigest()
        if stored is not None and (
            stored.ground_truth_sha256 != digest or stored.generator_version != demo.GENERATOR_VERSION
        ):
            stored.ground_truth_sha256 = digest
            stored.generator_version = demo.GENERATOR_VERSION
    return case


def _dns_exists(db: Session, case_id: uuid.UUID, item: dict[str, str]) -> bool:
    domain = db.scalar(select(DomainName).where(DomainName.name_norm == normalise_domain(item["domain"])))
    if domain is None:
        return False
    when = datetime.fromisoformat(item["observed_at"])
    found = db.scalar(
        select(DnsObservation.id).where(
            DnsObservation.case_id == case_id,
            DnsObservation.domain_id == domain.id,
            DnsObservation.rrtype == item["rrtype"],
            DnsObservation.rdata == normalise_ip(item["rdata"]),
            DnsObservation.observed_at == when,
        )
    )
    return found is not None


def _hosting_exists(db: Session, case_id: uuid.UUID, item: dict[str, str]) -> bool:
    address = db.scalar(select(IpAddress).where(IpAddress.address == normalise_ip(item["ip"])))
    if address is None:
        return False
    found = db.scalar(
        select(HostingObservation.id).where(
            HostingObservation.case_id == case_id,
            HostingObservation.ip_address_id == address.id,
            HostingObservation.provider_name == item["provider_name"],
            HostingObservation.observed_at == datetime.fromisoformat(item["observed_at"]),
        )
    )
    return found is not None


def _has_run(db: Session, case_id: uuid.UUID, kind: str) -> bool:
    found = db.scalar(
        select(AnalyticalRun.id).where(
            AnalyticalRun.case_id == case_id,
            AnalyticalRun.run_kind == kind,
            AnalyticalRun.status == "succeeded",
        )
    )
    return found is not None


def seed_demo(db: Session, settings: Settings, username: str) -> dict[str, object]:
    if settings.data_mode != "synthetic":
        raise SystemExit("SYN-DEMO is synthetic. Refusing to load it in operational mode.")
    principal = _principal(db, username)
    case = _case(db, settings, principal)
    for subject, filename, payload in demo.statements():
        job = ingestion_service.ingest_file(
            db,
            settings,
            principal,
            case_id=case.id,
            filename=filename,
            payload=payload,
            subject_account=subject,
            subject_ifsc=IFSC,
            subject_vpa=None,
            request_id=REQUEST_ID,
        )
        if job.status not in {"succeeded", "succeeded_with_errors"}:
            raise SystemExit(f"Statement {filename} did not load: {job.status}")
    for item in demo.dns_observations():
        if not _dns_exists(db, case.id, item):
            infrastructure_service.add_dns(
                db,
                principal,
                case_id=case.id,
                domain=item["domain"],
                rrtype=item["rrtype"],
                rdata=item["rdata"],
                observed_at=item["observed_at"],
                request_id=REQUEST_ID,
                resolver="synthetic_fixture",
            )
    for item in demo.hosting_observations():
        if not _hosting_exists(db, case.id, item):
            infrastructure_service.add_hosting(
                db,
                principal,
                case_id=case.id,
                ip=item["ip"],
                provider_name=item["provider_name"],
                source_note=item["source_note"],
                observed_at=item["observed_at"],
                request_id=REQUEST_ID,
            )
    for item in demo.gateway_records():
        bridge_service.add_gateway_record(db, principal, case_id=case.id, request_id=REQUEST_ID, **item)
    db.flush()
    if not _has_run(db, case.id, "trace"):
        seed = db.scalar(
            select(Transaction).where(
                Transaction.case_id == case.id, Transaction.source_transaction_id == "DEMO-V-1"
            )
        )
        if seed is None:
            raise SystemExit("The opening debit DEMO-V-1 is missing.")
        analysis_service.run_trace(
            db,
            principal,
            case_id=case.id,
            seed_transaction_ids=[seed.id],
            max_layer=3,
            currency="INR",
            request_id=REQUEST_ID,
        )
    if not _has_run(db, case.id, "indicators"):
        analysis_service.run_indicators(
            db,
            principal,
            case_id=case.id,
            window_start=date(2026, 1, 16),
            window_end=date(2026, 1, 17),
            fan_in_min=3,
            fan_out_min=3,
            pass_through_ratio=analysis_service.parse_amount("0.85"),
            pass_through_dwell_hours=analysis_service.parse_amount("24"),
            amount_floor=analysis_service.parse_amount("1000.0000"),
            currency="INR",
            request_id=REQUEST_ID,
        )
    # A second seed reruns correlation only when the stored source ids changed.
    # The trace and the indicator run stay. The added rows are outside that window
    # and are not the trace seed, so those stored results still describe the same inputs.
    latest_hash = db.scalar(
        select(AnalyticalRun.input_hash)
        .where(
            AnalyticalRun.case_id == case.id,
            AnalyticalRun.run_kind == "correlation",
            AnalyticalRun.status == "succeeded",
        )
        .order_by(AnalyticalRun.created_at.desc())
    )
    if latest_hash != correlation_input_hash(db, case.id):
        correlation_service.run_correlation(db, principal, case.id, REQUEST_ID)
    db.flush()
    return {"case_id": str(case.id), "reference": case.reference}


def main() -> None:
    parser = argparse.ArgumentParser(description="Load the synthetic SYN-DEMO investigation.")
    parser.add_argument("--username", required=True, help="Existing investigator who becomes the case lead.")
    args = parser.parse_args()
    settings = load_settings()
    init_engine(settings)
    db = open_session()
    try:
        result = seed_demo(db, settings, args.username)
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
    print(f"{result['reference']} {result['case_id']}")


if __name__ == "__main__":
    main()
