"""Deterministic synthetic datasets. Ground truth is not investigative evidence."""

import csv
import json
from io import StringIO

SEED = 20261122
IFSC = "SYNB0000001"


def transfer_csv(rows: list[dict[str, str]]) -> bytes:
    buffer = StringIO()
    fieldnames = [
        "source_transaction_id",
        "source_account",
        "source_ifsc",
        "destination_account",
        "destination_ifsc",
        "amount",
        "currency",
        "timestamp",
        "transaction_type",
        "payment_reference",
        "status",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8")


def _row(
    source_id: str,
    source: str,
    destination: str,
    amount: str,
    when: str,
    currency: str = "INR",
    status: str = "posted",
    kind: str = "imps",
) -> dict[str, str]:
    return {
        "source_transaction_id": source_id,
        "source_account": source,
        "source_ifsc": IFSC,
        "destination_account": destination,
        "destination_ifsc": IFSC,
        "amount": amount,
        "currency": currency,
        "timestamp": when,
        "transaction_type": kind,
        "payment_reference": f"REF-{source_id}",
        "status": status,
    }


def scenario_bundle() -> dict[str, bytes]:
    """Fixed fictional rows. Account numbers are synthetic placeholders."""
    normal = [
        _row("N1", "900000000001", "900000000002", "1500.50", "2026-02-01"),
        _row("N2", "900000000002", "900000000003", "250.0000", "2026-02-01T09:15:00"),
    ]
    chain = [
        _row("C1", "900000000011", "900000000012", "100000.0000", "2026-01-15T09:00:00"),
        _row("C2", "900000000012", "900000000013", "100000.0000", "2026-01-15T09:20:00"),
        _row("C3", "900000000013", "900000000014", "100000.0000", "2026-01-15T10:00:00"),
    ]
    fan_in = [
        _row("F1", "900000000021", "900000000030", "20000.0000", "2026-01-16"),
        _row("F2", "900000000022", "900000000030", "20000.0000", "2026-01-16"),
        _row("F3", "900000000023", "900000000030", "20000.0000", "2026-01-16"),
    ]
    fan_out = [
        _row(f"O{index}", "900000000030", f"90000000004{index}", "10000.0000", "2026-01-17")
        for index in range(1, 5)
    ]
    circular = [
        _row("R1", "900000000041", "900000000042", "5000.0000", "2026-01-18T11:00:00"),
        _row("R2", "900000000042", "900000000041", "5000.0000", "2026-01-18T12:00:00"),
    ]
    duplicate = [
        _row("D1", "900000000051", "900000000052", "10.0000", "2026-01-19"),
        _row("D1", "900000000051", "900000000052", "10.0000", "2026-01-19"),
    ]
    invalid = [_row("B1", "900000000061", "900000000062", "10.12345", "2026-01-20")]
    missing = [
        {
            "source_transaction_id": "M1",
            "source_account": "900000000071",
            "source_ifsc": IFSC,
            "destination_account": "",
            "destination_ifsc": "",
            "amount": "10.0000",
            "currency": "INR",
            "timestamp": "2026-01-21",
            "transaction_type": "imps",
            "payment_reference": "REF-M1",
            "status": "posted",
        }
    ]
    currencies = [
        _row("U1", "900000000081", "900000000082", "10.0000", "2026-01-22", currency="USD"),
        _row("U2", "900000000081", "900000000083", "10.0000", "19/01/2026", currency="INR"),
    ]
    files = {
        "normal.csv": transfer_csv(normal),
        "mule_chain.csv": transfer_csv(chain),
        "fan_in.csv": transfer_csv(fan_in),
        "fan_out.csv": transfer_csv(fan_out),
        "circular.csv": transfer_csv(circular),
        "duplicate.csv": transfer_csv(duplicate),
        "invalid.csv": transfer_csv(invalid),
        "missing.csv": transfer_csv(missing),
        "currencies.csv": transfer_csv(currencies),
    }
    files["normal.json"] = json.dumps(
        {"records": normal, "data_classification": "synthetic", "seed": SEED},
        indent=2,
    ).encode("utf-8")
    return files


def statement_csv(rows: list[dict[str, str]]) -> bytes:
    buffer = StringIO()
    fieldnames = [
        "line_number",
        "booking_date",
        "booking_time",
        "direction",
        "amount",
        "currency",
        "rail",
        "narration",
        "counterparty_account",
        "counterparty_ifsc",
        "reference",
        "source_transaction_id",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8")


def _leg(
    line: int,
    when: str,
    clock: str,
    direction: str,
    amount: str,
    counterparty: str,
    reference: str,
    source_id: str,
) -> dict[str, str]:
    return {
        "line_number": str(line),
        "booking_date": when,
        "booking_time": clock,
        "direction": direction,
        "amount": amount,
        "currency": "INR",
        "rail": "imps",
        "narration": "synthetic",
        "counterparty_account": counterparty,
        "counterparty_ifsc": IFSC,
        "reference": reference,
        "source_transaction_id": source_id,
    }


def intelligence_statements() -> list[tuple[str, str, bytes]]:
    """Subject account, filename, and statement bytes. Ground truth is separate."""
    chain = {
        "100000000001": [
            _leg(1, "2026-01-15", "09:00:00", "debit", "100000.0000", "100000000011", "UTRSYN0001", "S1-V")
        ],
        "100000000011": [
            _leg(
                1, "2026-01-15", "09:01:00", "credit", "100000.0000", "100000000001", "UTRSYN0001", "S1-I1-IN"
            ),
            _leg(
                2, "2026-01-15", "09:20:00", "debit", "100000.0000", "100000000012", "UTRSYN0002", "S1-I1-OUT"
            ),
        ],
        "100000000012": [
            _leg(
                1, "2026-01-15", "09:21:00", "credit", "100000.0000", "100000000011", "UTRSYN0002", "S1-I2-IN"
            ),
            _leg(
                2, "2026-01-15", "10:00:00", "debit", "100000.0000", "100000000013", "UTRSYN0003", "S1-I2-OUT"
            ),
        ],
        "100000000013": [
            _leg(
                1, "2026-01-15", "10:01:00", "credit", "100000.0000", "100000000012", "UTRSYN0003", "S1-I3-IN"
            ),
            _leg(
                2, "2026-01-15", "11:00:00", "debit", "100000.0000", "100000000019", "UTRSYN0004", "S1-I3-OUT"
            ),
        ],
        "100000000019": [
            _leg(1, "2026-01-15", "11:01:00", "credit", "100000.0000", "100000000013", "UTRSYN0004", "S1-B")
        ],
        "100000000030": [
            _leg(1, "2026-01-16", "09:00:00", "credit", "20000.0000", "100000000021", "FAN1", "S2-C1"),
            _leg(2, "2026-01-16", "09:05:00", "credit", "20000.0000", "100000000022", "FAN2", "S2-C2"),
            _leg(3, "2026-01-16", "09:10:00", "credit", "20000.0000", "100000000023", "FAN3", "S2-C3"),
            _leg(4, "2026-01-17", "15:00:00", "debit", "10000.0000", "100000000041", "OUT1", "S3-O1"),
            _leg(5, "2026-01-17", "15:05:00", "debit", "10000.0000", "100000000042", "OUT2", "S3-O2"),
            _leg(6, "2026-01-17", "15:10:00", "debit", "10000.0000", "100000000043", "OUT3", "S3-O3"),
            _leg(7, "2026-01-17", "15:15:00", "debit", "10000.0000", "100000000044", "OUT4", "S3-O4"),
        ],
    }
    for index, source in enumerate(("100000000021", "100000000022", "100000000023"), start=1):
        chain[source] = [
            _leg(
                1,
                "2026-01-16",
                "08:59:00",
                "debit",
                "20000.0000",
                "100000000030",
                f"FAN{index}",
                f"S2-D{index}",
            )
        ]
    chain["100000000051"] = [
        _leg(1, "2026-01-18", "12:00:00", "debit", "100000.0000", "100000000052", "UNREL", "S4-U")
    ]
    chain["100000000052"] = [
        _leg(1, "2026-01-18", "12:01:00", "credit", "100000.0000", "100000000051", "UNREL", "S4-U-IN")
    ]
    return [(subject, f"{subject}.csv", statement_csv(rows)) for subject, rows in chain.items()]


def analysis_ground_truth() -> dict[str, object]:
    """Expected analytical results. Written from the scenario, not from a detector run."""
    return {
        "data_classification": "synthetic",
        "note": "Ground truth for tests. Not a finding and not discovered intelligence.",
        "horizon_3_flows": [
            ["100000000001", "100000000011", 1],
            ["100000000011", "100000000012", 2],
            ["100000000012", "100000000013", 3],
        ],
        "horizon_3_residual": ["100000000013", "outside_horizon"],
        "horizon_3_absent": "100000000019",
        "horizon_4_destination": "100000000019",
        "fan_in_account_tail": "0030",
        "fan_out_account_tail": "0030",
        "pass_through_at_default_ratio": False,
        "unrelated_source_tail": "0051",
    }


def ground_truth() -> dict[str, object]:
    return {
        "data_classification": "synthetic",
        "seed": SEED,
        "note": "This file is ground truth for tests. It is not a finding.",
        "expected_inserted": {
            "normal.csv": ["N1", "N2"],
            "mule_chain.csv": ["C1", "C2", "C3"],
            "fan_in.csv": ["F1", "F2", "F3"],
            "fan_out.csv": ["O1", "O2", "O3", "O4"],
            "circular.csv": ["R1", "R2"],
            "duplicate.csv": ["D1"],
            "invalid.csv": [],
            "missing.csv": [],
            "currencies.csv": ["U1", "U2"],
            "normal.json": ["N1", "N2"],
        },
        "expected_issue_categories": {
            "duplicate.csv": ["exact_duplicate"],
            "invalid.csv": ["invalid_amount"],
            "missing.csv": ["missing_field"],
        },
    }
