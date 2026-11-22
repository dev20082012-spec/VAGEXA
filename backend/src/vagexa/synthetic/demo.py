"""SYN-DEMO. One fictional investigation. Ground truth is written by hand and is not served by the API."""

from vagexa.synthetic.datasets import IFSC, SEED, statement_csv

REFERENCE = "SYN-DEMO"
TITLE = (
    "Determine which records connect a fictional merchant payment to later transfers, "
    "and which links remain unresolved"
)
OPENED_ON = "2026-01-20"
SCENARIO_KEY = "hackathon-demo"
GENERATOR_VERSION = "demo.v2"
VICTIM = "100000000001"
I1 = "100000000011"
I2 = "100000000012"
I3 = "100000000013"
BENEFICIARY = "100000000019"
COLLECTOR = "100000000030"
ORDINARY = "100000000060"
DISPUTED_PAYER = "100000000070"
DISPUTED_PAYEE = "100000000071"


def _leg(
    line: int,
    when: str,
    clock: str,
    direction: str,
    amount: str,
    counterparty: str,
    reference: str,
    source_id: str,
    narration: str = "synthetic transfer",
) -> dict[str, str]:
    return {
        "line_number": str(line),
        "booking_date": when,
        "booking_time": clock,
        "direction": direction,
        "amount": amount,
        "currency": "INR",
        "rail": "imps",
        "narration": narration,
        "counterparty_account": counterparty,
        "counterparty_ifsc": IFSC,
        "reference": reference,
        "source_transaction_id": source_id,
    }


def statements() -> list[tuple[str, str, bytes]]:
    rows: dict[str, list[dict[str, str]]] = {
        VICTIM: [
            _leg(
                1,
                "2026-01-15",
                "09:00:00",
                "debit",
                "100000.0000",
                I1,
                "UTRSYN0001",
                "DEMO-V-1",
                "UPI payment to merchant syn-a.test order SYN-ORD-7741",
            ),
        ],
        I1: [
            _leg(1, "2026-01-15", "09:01:00", "credit", "100000.0000", VICTIM, "UTRSYN0001", "DEMO-I1-IN"),
            _leg(2, "2026-01-15", "09:20:00", "debit", "100000.0000", I2, "UTRSYN0002", "DEMO-I1-OUT"),
        ],
        I2: [
            _leg(1, "2026-01-15", "09:21:00", "credit", "100000.0000", I1, "UTRSYN0002", "DEMO-I2-IN"),
            _leg(2, "2026-01-15", "10:00:00", "debit", "100000.0000", I3, "UTRSYN0003", "DEMO-I2-OUT"),
        ],
        I3: [
            _leg(1, "2026-01-15", "10:01:00", "credit", "100000.0000", I2, "UTRSYN0003", "DEMO-I3-IN"),
            _leg(
                2, "2026-01-15", "11:00:00", "debit", "100000.0000", BENEFICIARY, "UTRSYN0004", "DEMO-I3-OUT"
            ),
        ],
        BENEFICIARY: [
            _leg(1, "2026-01-15", "11:01:00", "credit", "100000.0000", I3, "UTRSYN0004", "DEMO-B-IN"),
        ],
        COLLECTOR: [
            _leg(1, "2026-01-16", "09:00:00", "credit", "20000.0000", "100000000021", "FAN1", "DEMO-C-IN-1"),
            _leg(2, "2026-01-16", "09:05:00", "credit", "20000.0000", "100000000022", "FAN2", "DEMO-C-IN-2"),
            _leg(3, "2026-01-16", "09:10:00", "credit", "20000.0000", "100000000023", "FAN3", "DEMO-C-IN-3"),
            _leg(4, "2026-01-17", "15:00:00", "debit", "10000.0000", "100000000041", "OUT1", "DEMO-C-OUT-1"),
            _leg(5, "2026-01-17", "15:05:00", "debit", "10000.0000", "100000000042", "OUT2", "DEMO-C-OUT-2"),
            _leg(6, "2026-01-17", "15:10:00", "debit", "10000.0000", "100000000043", "OUT3", "DEMO-C-OUT-3"),
            _leg(7, "2026-01-17", "15:15:00", "debit", "10000.0000", "100000000044", "OUT4", "DEMO-C-OUT-4"),
        ],
        "100000000051": [
            _leg(1, "2026-01-18", "12:00:00", "debit", "100000.0000", "100000000052", "UNREL", "DEMO-U-OUT")
        ],
        "100000000052": [
            _leg(1, "2026-01-18", "12:01:00", "credit", "100000.0000", "100000000051", "UNREL", "DEMO-U-IN")
        ],
        DISPUTED_PAYER: [
            _leg(
                1,
                "2026-01-19",
                "14:00:00",
                "debit",
                "2500.0000",
                DISPUTED_PAYEE,
                "UTRSYN0090",
                "DEMO-D-OUT",
                "synthetic service charge",
            )
        ],
        DISPUTED_PAYEE: [
            _leg(
                1,
                "2026-01-19",
                "14:01:00",
                "credit",
                "2500.0000",
                DISPUTED_PAYER,
                "UTRSYN0090",
                "DEMO-D-IN",
                "synthetic service charge",
            )
        ],
        ORDINARY: [
            _leg(
                1,
                "2026-01-10",
                "10:00:00",
                "credit",
                "45000.0000",
                "100000000061",
                "SAL-0126",
                "DEMO-N-1",
                "salary January synthetic employer",
            ),
            _leg(
                2,
                "2026-01-12",
                "18:30:00",
                "debit",
                "1820.5000",
                "100000000062",
                "ELEC-0126",
                "DEMO-N-2",
                "electricity bill synthetic utility",
            ),
            _leg(
                3,
                "2026-01-14",
                "20:15:00",
                "debit",
                "499.0000",
                "100000000063",
                "SHOP-0126",
                "DEMO-N-3",
                "online order refund syn-aa.test",
            ),
        ],
    }
    for index, source in enumerate(("100000000021", "100000000022", "100000000023"), start=1):
        rows[source] = [
            _leg(
                1,
                "2026-01-16",
                "08:59:00",
                "debit",
                "20000.0000",
                COLLECTOR,
                f"FAN{index}",
                f"DEMO-F-{index}",
            )
        ]
    return [
        (subject, f"{REFERENCE.lower()}-{subject}.csv", statement_csv(items))
        for subject, items in rows.items()
    ]


def dns_observations() -> list[dict[str, str]]:
    return [
        {
            "domain": "syn-a.test",
            "rrtype": "A",
            "rdata": "203.0.113.50",
            "observed_at": "2026-01-14T10:00:00+00:00",
        },
        {
            "domain": "syn-b.test",
            "rrtype": "A",
            "rdata": "203.0.113.50",
            "observed_at": "2026-01-16T09:05:00+00:00",
        },
        {
            "domain": "syn-a.test",
            "rrtype": "A",
            "rdata": "203.0.113.60",
            "observed_at": "2026-01-20T10:00:00+00:00",
        },
        {
            "domain": "syn-c.test",
            "rrtype": "AAAA",
            "rdata": "2001:db8::50",
            "observed_at": "2026-01-16T12:00:00+00:00",
        },
        {
            "domain": "syn-d.test",
            "rrtype": "A",
            "rdata": "203.0.113.80",
            "observed_at": "2026-01-19T08:00:00+00:00",
        },
        {
            "domain": "syn-e.test",
            "rrtype": "A",
            "rdata": "203.0.113.81",
            "observed_at": "2026-01-19T08:00:00+00:00",
        },
    ]


def hosting_observations() -> list[dict[str, str]]:
    return [
        {
            "ip": "203.0.113.70",
            "provider_name": "Synthetic Shared Host",
            "source_note": "Synthetic note: unrelated customer on a shared hosting provider.",
            "observed_at": "2026-01-16T11:00:00+00:00",
        },
        {
            "ip": "203.0.113.71",
            "provider_name": "Synthetic Shared Host",
            "source_note": "Synthetic note: a different customer on the same provider string.",
            "observed_at": "2026-01-16T11:05:00+00:00",
        },
    ]


def gateway_records() -> list[dict[str, str]]:
    return [
        {
            "source_record_id": "SYN-PG-0001",
            "source_system": "synthetic_payment_gateway",
            "payment_reference": "UTRSYN0001",
            "payer_account": VICTIM,
            "payer_ifsc": IFSC,
            "payee_account": I1,
            "payee_ifsc": IFSC,
            "merchant_domain": "syn-a.test",
            "merchant_label": "Synthetic Merchant A",
            "amount": "100000.0000",
            "currency": "INR",
            "processed_at": "2026-01-15T03:30:20+00:00",
        },
        {
            "source_record_id": "SYN-PG-0090",
            "source_system": "synthetic_payment_gateway",
            "payment_reference": "UTRSYN0090",
            "payer_account": DISPUTED_PAYER,
            "payer_ifsc": IFSC,
            "payee_account": DISPUTED_PAYEE,
            "payee_ifsc": IFSC,
            "merchant_domain": "syn-d.test",
            "merchant_label": "Synthetic Service D",
            "amount": "2500.0000",
            "currency": "INR",
            "processed_at": "2026-01-19T14:00:30+00:00",
        },
        {
            "source_record_id": "SYN-PG-0091",
            "source_system": "synthetic_payment_gateway",
            "payment_reference": "UTRSYN0090",
            "payer_account": DISPUTED_PAYER,
            "payer_ifsc": IFSC,
            "payee_account": DISPUTED_PAYEE,
            "payee_ifsc": IFSC,
            "merchant_domain": "syn-e.test",
            "merchant_label": "Synthetic Service E",
            "amount": "2500.0000",
            "currency": "INR",
            "processed_at": "2026-01-19T14:00:40+00:00",
        },
    ]


def ground_truth() -> dict[str, object]:
    """What a reader of the scenario expects. Not computed from any detector."""
    return {
        "data_classification": "synthetic",
        "seed": SEED,
        "reference": REFERENCE,
        "title": TITLE,
        "status": "open",
        "opened_on": OPENED_ON,
        "transactions": 25,
        "statements": 14,
        "dns_observations": 6,
        "hosting_observations": 2,
        "gateway_records": 3,
        "same_payment_pairs": 9,
        "relationships": 15,
        "findings": 18,
        "statement_debits": "604819.5000",
        "statement_credits": "607500.0000",
        "trace_seed_source_id": "DEMO-V-1",
        "trace_layers": [
            ["****0001", "****0011", 1],
            ["****0011", "****0012", 2],
            ["****0012", "****0013", 3],
        ],
        "trace_residual": ["****0013", "outside_horizon", "100000.0000"],
        "not_attributed_at_horizon_3": "****0019",
        "not_in_trace": ["****0019", "****0030", "****0051", "****0070", "****0071"],
        "indicators": [["FAN_IN", "****0030"], ["FAN_OUT", "****0030"]],
        "indicator_configuration": {
            "window_start": "2026-01-16",
            "window_end": "2026-01-17",
            "fan_in_min": 3,
            "fan_out_min": 3,
            "pass_through_ratio": "0.85",
            "currency": "INR",
        },
        "pass_through_at_default_ratio": False,
        "activity": {
            "****0001": {"incoming_amount": "0.0000", "outgoing_amount": "100000.0000"},
            "****0030": {
                "incoming_amount": "60000.0000",
                "outgoing_amount": "40000.0000",
                "incoming_count": 3,
                "outgoing_count": 4,
            },
            "****0060": {"incoming_amount": "45000.0000", "outgoing_amount": "2319.5000"},
            "****0070": {"incoming_amount": "0.0000", "outgoing_amount": "2500.0000"},
            "****0071": {"incoming_amount": "2500.0000", "outgoing_amount": "0.0000"},
        },
        "opening_transfer": {
            "source_transaction_id": "DEMO-V-1",
            "from": "****0001",
            "to": "****0011",
            "amount": "100000.0000",
            "currency": "INR",
            "reference": "UTRSYN0001",
            "booking_date": "2026-01-15",
            "booking_time": "09:00:00",
        },
        "gateway_merchant": {"account": "****0011", "domain": "syn-a.test", "classification": "CORROBORATED"},
        "mentioned_in": {"account": "****0001", "domain": "syn-a.test", "classification": "CORROBORATED"},
        "contradicted_gateways": {
            "reference": "UTRSYN0090",
            "source_record_ids": ["SYN-PG-0090", "SYN-PG-0091"],
            "domains": ["syn-d.test", "syn-e.test"],
            "account": "****0071",
            "classification": "CONTRADICTED",
            "amount": "2500.0000",
        },
        "overlap_domains": ["syn-a.test", "syn-b.test"],
        "overlap_classification": "UNRESOLVED",
        "overlap_count": 2,
        "cross_domain_by_classification": {"CONTRADICTED": 2, "CORROBORATED": 2},
        "no_account_link": ["syn-b.test", "syn-c.test", "syn-aa.test"],
        "temporal_only": {"account": "****0030", "domain": "syn-b.test"},
        "missing_identifier": {"source_transaction_id": "DEMO-N-3", "host": "syn-aa.test"},
        "dns_history": {"syn-a.test": ["203.0.113.50", "203.0.113.60"]},
    }
