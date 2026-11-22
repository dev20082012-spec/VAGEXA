"""Store investigator-supplied infrastructure observations. Live lookup stays off."""

import csv
import json
import uuid
from datetime import UTC, datetime
from io import StringIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from vagexa.adapters.persistence.audit import append_audit
from vagexa.adapters.persistence.models import (
    Case,
    CaseAssignment,
    DnsObservation,
    DomainName,
    HostingObservation,
    IpAddress,
    ProvenanceRecord,
)
from vagexa.api.errors import Problem
from vagexa.application.auth_service import Principal
from vagexa.config import Settings
from vagexa.domain.authorization import case_role_allows
from vagexa.intelligence.digital.normalise import (
    OVERLAP_LIMITATION,
    IndicatorRejected,
    ip_version,
    normalise_domain,
    normalise_ip,
    refuse_lookup_target,
)

OBSERVE_VERSION = "observe.v1"
MAX_IMPORT = 500


def _case(
    db: Session, principal: Principal, case_id: uuid.UUID, *, write: bool, request_id: str | None
) -> Case:
    case = db.get(Case, case_id)
    assignment = db.get(CaseAssignment, (case_id, principal.id))
    permission = "cases.mutate" if write else "cases.read"
    if case is None or assignment is None or not case_role_allows(assignment.case_role, permission):
        append_audit(
            db,
            action="infrastructure.observe",
            outcome="denied",
            object_kind="case",
            actor_id=principal.id,
            case_id=case.id if case and assignment else None,
            object_id=str(case_id),
            request_id=request_id,
        )
        if case is None or assignment is None:
            raise Problem(404, "not-found", "Not available", "This case is not available.")
        raise Problem(403, "forbidden", "Not allowed", "You cannot record infrastructure for this case.")
    return case


def _when(raw: str) -> datetime:
    text = raw.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise IndicatorRejected("invalid_time", "The observation time is not an ISO timestamp.") from exc
    if parsed.tzinfo is None:
        raise IndicatorRejected("invalid_time", "The observation time needs a time zone.")
    return parsed.astimezone(UTC)


def _domain(db: Session, name: str) -> DomainName:
    found = db.scalar(select(DomainName).where(DomainName.name_norm == name))
    if found is not None:
        return found
    row = DomainName(name_norm=name)
    db.add(row)
    db.flush()
    return row


def _ip(db: Session, address: str) -> IpAddress:
    found = db.scalar(select(IpAddress).where(IpAddress.address == address))
    if found is not None:
        return found
    row = IpAddress(address=address)
    db.add(row)
    db.flush()
    return row


def _provenance(db: Session, case: Case, principal: Principal, reference: str) -> ProvenanceRecord:
    row = ProvenanceRecord(
        data_classification=case.data_classification,
        source_system="investigator_entry",
        source_reference=reference,
        collected_at=datetime.now(UTC),
        collected_by=str(principal.id),
        method_name=OBSERVE_VERSION,
        raw_hash=None,
    )
    db.add(row)
    db.flush()
    return row


def add_dns(
    db: Session,
    principal: Principal,
    *,
    case_id: uuid.UUID,
    domain: str,
    rrtype: str,
    rdata: str,
    observed_at: str,
    request_id: str | None,
    resolver: str = "investigator_entry",
) -> DnsObservation:
    case = _case(db, principal, case_id, write=True, request_id=request_id)
    try:
        name = normalise_domain(domain)
        family = rrtype.strip().upper()
        if family not in {"A", "AAAA"}:
            raise IndicatorRejected("unsupported_rrtype", "Phase 1 stores A and AAAA observations only.")
        address = normalise_ip(rdata)
        if (family == "A" and ip_version(address) != 4) or (family == "AAAA" and ip_version(address) != 6):
            raise IndicatorRejected("invalid_ip", "The address family does not match the record type.")
        when = _when(observed_at)
    except IndicatorRejected as exc:
        raise Problem(422, exc.code, "Invalid indicator", exc.message) from exc
    domain_row = _domain(db, name)
    ip_row = _ip(db, address)
    provenance = _provenance(db, case, principal, f"dns:{name}:{family}")
    row = DnsObservation(
        case_id=case.id,
        domain_id=domain_row.id,
        rrtype=family,
        rdata=address,
        ip_address_id=ip_row.id,
        observed_at=when,
        resolver=resolver,
        data_classification=case.data_classification,
        provenance_id=provenance.id,
    )
    db.add(row)
    db.flush()
    append_audit(
        db,
        action="infrastructure.observe",
        outcome="success",
        object_kind="dns_observation",
        actor_id=principal.id,
        case_id=case.id,
        object_id=str(row.id),
        request_id=request_id,
        detail={"kind": "dns", "rrtype": family, "resolver": resolver},
    )
    return row


def add_hosting(
    db: Session,
    principal: Principal,
    *,
    case_id: uuid.UUID,
    ip: str | None,
    provider_name: str | None,
    source_note: str,
    observed_at: str,
    request_id: str | None,
) -> HostingObservation:
    case = _case(db, principal, case_id, write=True, request_id=request_id)
    note = source_note.strip()
    if not note or len(note) > 2000:
        raise Problem(422, "invalid_note", "Invalid note", "The hosting note must be 1 to 2000 characters.")
    provider = provider_name.strip() if provider_name and provider_name.strip() else None
    try:
        address = normalise_ip(ip) if ip and ip.strip() else None
        when = _when(observed_at)
    except IndicatorRejected as exc:
        raise Problem(422, exc.code, "Invalid indicator", exc.message) from exc
    if address is None and provider is None:
        raise Problem(
            422, "missing_field", "Missing indicator", "A hosting note needs an address or a provider."
        )
    ip_row = _ip(db, address) if address else None
    provenance = _provenance(db, case, principal, "hosting")
    row = HostingObservation(
        case_id=case.id,
        ip_address_id=ip_row.id if ip_row else None,
        provider_name=provider,
        source_note=note,
        observed_at=when,
        data_classification=case.data_classification,
        provenance_id=provenance.id,
    )
    db.add(row)
    db.flush()
    append_audit(
        db,
        action="infrastructure.observe",
        outcome="success",
        object_kind="hosting_observation",
        actor_id=principal.id,
        case_id=case.id,
        object_id=str(row.id),
        request_id=request_id,
        detail={"kind": "hosting"},
    )
    return row


def list_observations(db: Session, principal: Principal, case_id: uuid.UUID) -> dict[str, object]:
    case = _case(db, principal, case_id, write=False, request_id=None)
    dns_rows = db.execute(
        select(DnsObservation, DomainName)
        .join(DomainName, DomainName.id == DnsObservation.domain_id)
        .where(DnsObservation.case_id == case.id)
        .order_by(DnsObservation.observed_at, DnsObservation.id)
    ).all()
    hosting_rows = list(
        db.scalars(
            select(HostingObservation)
            .where(HostingObservation.case_id == case.id)
            .order_by(HostingObservation.observed_at, HostingObservation.id)
        )
    )
    ip_ids = {row.ip_address_id for row, _domain in dns_rows if row.ip_address_id}
    ip_ids |= {row.ip_address_id for row in hosting_rows if row.ip_address_id}
    addresses = (
        {row.id: str(row.address) for row in db.scalars(select(IpAddress).where(IpAddress.id.in_(ip_ids)))}
        if ip_ids
        else {}
    )
    return {
        "data_classification": case.data_classification,
        "limitation": OVERLAP_LIMITATION,
        "registration": [],
        "registration_reason": "not_collected",
        "certificates": [],
        "certificate_reason": "not_collected",
        "dns": [
            {
                "id": str(row.id),
                "domain": domain.name_norm,
                "domain_id": str(domain.id),
                "rrtype": row.rrtype,
                "rdata": row.rdata,
                "observed_at": row.observed_at.isoformat(),
                "resolver": row.resolver,
                "provenance_id": str(row.provenance_id),
                "data_classification": row.data_classification,
            }
            for row, domain in dns_rows
        ],
        "hosting": [
            {
                "id": str(row.id),
                "ip": addresses.get(row.ip_address_id) if row.ip_address_id else None,
                "provider_name": row.provider_name,
                "source_note": row.source_note,
                "observed_at": row.observed_at.isoformat(),
                "provenance_id": str(row.provenance_id),
                "data_classification": row.data_classification,
            }
            for row in hosting_rows
        ],
    }


def _records_from_upload(filename: str, payload: bytes) -> list[dict[str, str]]:
    if len(payload) > 1_000_000:
        raise Problem(413, "payload-too-large", "File too large", "The infrastructure file exceeds 1 MB.")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeError as exc:
        raise Problem(422, "invalid_encoding", "Invalid encoding", "The file is not UTF-8.") from exc
    if filename.lower().endswith(".json") or text.lstrip().startswith(("{", "[")):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise Problem(
                422, "malformed_json", "Malformed JSON", "The infrastructure file is not JSON."
            ) from exc
        rows = parsed.get("records") if isinstance(parsed, dict) else parsed
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise Problem(
                422, "malformed_json", "Malformed JSON", "JSON observations must be a list of objects."
            )
        return [{key: "" if value is None else str(value) for key, value in row.items()} for row in rows]
    reader = csv.DictReader(StringIO(text))
    if reader.fieldnames is None:
        raise Problem(422, "missing_columns", "Missing columns", "The CSV needs a header.")
    return [{key: value or "" for key, value in row.items() if key} for row in reader]


def import_observations(
    db: Session,
    principal: Principal,
    *,
    case_id: uuid.UUID,
    filename: str,
    payload: bytes,
    request_id: str | None,
) -> dict[str, object]:
    _case(db, principal, case_id, write=True, request_id=request_id)
    records = _records_from_upload(filename, payload)
    if not records:
        raise Problem(422, "empty_file", "Empty file", "The file has no observations.")
    if len(records) > MAX_IMPORT:
        raise Problem(
            422, "too_many_records", "Too many records", "An import is limited to 500 observations."
        )
    inserted = 0
    errors: list[dict[str, object]] = []
    for index, record in enumerate(records, start=1):
        kind = record.get("kind", "dns").strip().lower()
        try:
            if kind == "dns":
                add_dns(
                    db,
                    principal,
                    case_id=case_id,
                    domain=record.get("domain", ""),
                    rrtype=record.get("rrtype", ""),
                    rdata=record.get("rdata", ""),
                    observed_at=record.get("observed_at", ""),
                    request_id=request_id,
                )
            elif kind == "hosting":
                add_hosting(
                    db,
                    principal,
                    case_id=case_id,
                    ip=record.get("ip") or record.get("rdata"),
                    provider_name=record.get("provider_name"),
                    source_note=record.get("source_note") or record.get("note") or "Imported hosting note.",
                    observed_at=record.get("observed_at", ""),
                    request_id=request_id,
                )
            else:
                raise Problem(
                    422,
                    "unsupported_kind",
                    "Unsupported indicator",
                    "This release stores dns and hosting only. Certificates and RDAP are not collected.",
                )
        except Problem as exc:
            errors.append({"line_number": index, "category": exc.type_slug, "message": exc.detail})
            continue
        inserted += 1
    return {"inserted": inserted, "errors": errors, "data_classification": "see case"}


def request_passive_lookup(settings: Settings, domain: str) -> None:
    """The live resolver is not called. Private targets are refused before any network decision."""
    if not settings.passive_intel:
        raise Problem(
            409,
            "passive-intel-off",
            "Live lookup is off",
            "Enter the DNS answer as an observation. This deployment does not resolve names.",
        )
    refusal = refuse_lookup_target(domain)
    if refusal is not None:
        raise Problem(422, refusal.code, "Lookup refused", refusal.message)
    raise Problem(
        409,
        "no-resolver",
        "No resolver is configured",
        "Live DNS is not collected. Enter the observation the investigator already holds.",
    )
