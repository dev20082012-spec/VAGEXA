"""Synthetic infrastructure observations. Ground truth is not a finding of ownership."""


def shared_ip_records() -> list[dict[str, str]]:
    return [
        {
            "kind": "dns",
            "domain": "syn-a.test",
            "rrtype": "A",
            "rdata": "203.0.113.50",
            "observed_at": "2026-01-16T09:00:00Z",
        },
        {
            "kind": "dns",
            "domain": "syn-b.test",
            "rrtype": "A",
            "rdata": "203.0.113.50",
            "observed_at": "2026-01-16T09:05:00Z",
        },
        {
            "kind": "dns",
            "domain": "syn-a.test",
            "rrtype": "A",
            "rdata": "203.0.113.60",
            "observed_at": "2026-01-17T09:00:00Z",
        },
        {
            "kind": "dns",
            "domain": "syn-e.test",
            "rrtype": "A",
            "rdata": "203.0.113.10",
            "observed_at": "2026-01-16T10:00:00Z",
        },
        {
            "kind": "dns",
            "domain": "syn-e.test",
            "rrtype": "A",
            "rdata": "203.0.113.11",
            "observed_at": "2026-01-18T10:00:00Z",
        },
        {
            "kind": "hosting",
            "ip": "203.0.113.70",
            "provider_name": "Synthetic Shared Host",
            "source_note": "Unrelated customer on shared hosting. Synthetic.",
            "observed_at": "2026-01-16T11:00:00Z",
        },
        {
            "kind": "hosting",
            "ip": "203.0.113.71",
            "provider_name": "Synthetic Shared Host",
            "source_note": "A different customer on the same provider string. Synthetic.",
            "observed_at": "2026-01-16T11:05:00Z",
        },
    ]


def ground_truth() -> dict[str, object]:
    return {
        "data_classification": "synthetic",
        "note": "Planted observations for tests. Shared keys are not common ownership.",
        "shared_ip_domains": ["syn-a.test", "syn-b.test"],
        "shared_ip": "203.0.113.50",
        "conflicting_answers": ["203.0.113.50", "203.0.113.60"],
        "address_change": ["203.0.113.10", "203.0.113.11"],
        "shared_provider": "Synthetic Shared Host",
        "ownership": False,
        "registration_collected": False,
        "certificates_collected": False,
    }
