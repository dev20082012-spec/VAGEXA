"""Indicator rules against hand-built rows. Thresholds are the documented demonstration settings."""

from datetime import date, time
from decimal import Decimal

from vagexa.intelligence.financial.activity import summarise
from vagexa.intelligence.financial.indicators import EXCLUSION, detect
from vagexa.intelligence.financial.ledger import LedgerRow
from vagexa.intelligence.financial.walk import walk_statements

D = date(2026, 1, 16)


def _row(
    row_id: str,
    account: str,
    direction: str,
    counterparty: str,
    amount: str,
    line: int,
    clock: str | None = None,
    reference: str | None = None,
    resolution: str = "structured_field",
    booked: date = D,
    currency: str = "INR",
) -> LedgerRow:
    return LedgerRow(
        row_id,
        account,
        direction,
        Decimal(amount),
        currency,
        booked,
        time.fromisoformat(clock) if clock else None,
        line,
        counterparty,
        resolution,
        reference,
        "imps",
        "time" if clock else "date",
    )


def fan_in_rows() -> list[LedgerRow]:
    rows = []
    for index, source in enumerate(("100000000021", "100000000022", "100000000023"), start=1):
        reference = f"F{index}"
        rows.append(_row(f"D{index}", source, "debit", "100000000030", "20000.0000", 1, reference=reference))
        rows.append(
            _row(f"C{index}", "100000000030", "credit", source, "20000.0000", index, reference=reference)
        )
    return rows


def test_fan_in_fires_at_three_and_not_at_four() -> None:
    fired = detect(
        fan_in_rows(),
        currency="INR",
        window_start=D,
        window_end=D,
        fan_in_min=3,
        fan_out_min=3,
        pass_through_ratio=Decimal("0.85"),
        pass_through_dwell_hours=Decimal(24),
        amount_floor=Decimal("1000.0000"),
    )
    codes = [(hit.code, hit.account_id, hit.support_transaction_ids) for hit in fired.hits]
    assert ("FAN_IN", "100000000030", ["C1", "C2", "C3"]) in codes
    quiet = detect(
        fan_in_rows(),
        currency="INR",
        window_start=D,
        window_end=D,
        fan_in_min=4,
        fan_out_min=3,
        pass_through_ratio=Decimal("0.85"),
        pass_through_dwell_hours=Decimal(24),
        amount_floor=Decimal("1000.0000"),
    )
    assert all(hit.code != "FAN_IN" for hit in quiet.hits)


def test_two_sources_do_not_fire() -> None:
    result = detect(
        fan_in_rows()[:4],
        currency="INR",
        window_start=D,
        window_end=D,
        fan_in_min=3,
        fan_out_min=3,
        pass_through_ratio=Decimal("0.85"),
        pass_through_dwell_hours=Decimal(24),
        amount_floor=Decimal("1000.0000"),
    )
    assert result.hits == []
    assert result.limitations == EXCLUSION


def test_narration_edge_does_not_increase_the_count() -> None:
    rows = fan_in_rows()[:4]
    rows.append(
        _row(
            "N1",
            "100000000030",
            "credit",
            "100000000099",
            "20000.0000",
            9,
            reference="NARR",
            resolution="narration_pattern",
        )
    )
    result = detect(
        rows,
        currency="INR",
        window_start=D,
        window_end=D,
        fan_in_min=3,
        fan_out_min=3,
        pass_through_ratio=Decimal("0.85"),
        pass_through_dwell_hours=Decimal(24),
        amount_floor=Decimal("1000.0000"),
    )
    assert all(hit.code != "FAN_IN" for hit in result.hits)


def test_fan_out_and_pass_through_threshold() -> None:
    rows = fan_in_rows()
    for index in range(1, 5):
        rows.append(
            _row(
                f"O{index}",
                "100000000030",
                "debit",
                f"10000000004{index}",
                "10000.0000",
                index,
                clock="15:00:00",
                reference=f"O{index}",
                booked=date(2026, 1, 17),
            )
        )
    result = detect(
        rows,
        currency="INR",
        window_start=D,
        window_end=date(2026, 1, 17),
        fan_in_min=3,
        fan_out_min=3,
        pass_through_ratio=Decimal("0.85"),
        pass_through_dwell_hours=Decimal(24),
        amount_floor=Decimal("1000.0000"),
    )
    codes = {hit.code for hit in result.hits if hit.account_id == "100000000030"}
    assert "FAN_OUT" in codes
    assert "PASS_THROUGH" not in codes
    lowered = detect(
        rows,
        currency="INR",
        window_start=D,
        window_end=date(2026, 1, 17),
        fan_in_min=3,
        fan_out_min=3,
        pass_through_ratio=Decimal("0.50"),
        pass_through_dwell_hours=Decimal(48),
        amount_floor=Decimal("1000.0000"),
    )
    passed = next(hit for hit in lowered.hits if hit.code == "PASS_THROUGH")
    assert "not a FIFO allocation" in passed.limitations
    assert "Dwell was not applied" in passed.limitations


def test_date_only_pass_through_does_not_claim_a_dwell() -> None:
    rows = [
        _row("IN", "C", "credit", "A", "2000.0000", 1, reference="IN"),
        _row("OUT", "C", "debit", "B", "2000.0000", 2, reference="OUT"),
    ]
    result = detect(
        rows,
        currency="INR",
        window_start=D,
        window_end=D,
        fan_in_min=3,
        fan_out_min=3,
        pass_through_ratio=Decimal("0.85"),
        pass_through_dwell_hours=Decimal(24),
        amount_floor=Decimal("1000.0000"),
    )
    hit = next(item for item in result.hits if item.code == "PASS_THROUGH")
    assert "Dwell was not applied" in hit.limitations
    assert "24" not in hit.limitations


def test_slow_movement_does_not_fire_pass_through() -> None:
    rows = [
        _row("IN", "C", "credit", "A", "2000.0000", 1, clock="09:00:00", reference="IN"),
        _row(
            "OUT",
            "C",
            "debit",
            "B",
            "2000.0000",
            2,
            clock="09:00:00",
            reference="OUT",
            booked=date(2026, 1, 18),
        ),
    ]
    result = detect(
        rows,
        currency="INR",
        window_start=D,
        window_end=date(2026, 1, 18),
        fan_in_min=9,
        fan_out_min=9,
        pass_through_ratio=Decimal("0.85"),
        pass_through_dwell_hours=Decimal(24),
        amount_floor=Decimal("1000.0000"),
    )
    assert all(hit.code != "PASS_THROUGH" for hit in result.hits)


def test_activity_does_not_add_currencies_or_invent_a_baseline() -> None:
    rows = [
        _row("A", "ACCT", "credit", "B", "10.1000", 1, currency="INR"),
        _row("B", "ACCT", "credit", "C", "10.2000", 2, currency="USD"),
        _row("C", "ACCT", "debit", "D", "0.3000", 3, currency="INR"),
    ]
    metrics = summarise(rows)
    inr = next(item for item in metrics if item.currency == "INR")
    usd = next(item for item in metrics if item.currency == "USD")
    assert f"{inr.incoming_amount:.4f}" == "10.1000"
    assert f"{usd.incoming_amount:.4f}" == "10.2000"
    assert "not converted" in inr.coverage
    assert "dormant-to-active comparison is not made" in inr.coverage
    assert f"{inr.average_amount:.4f}" == "5.2000"


def test_walk_stops_at_depth_and_does_not_label_a_cycle() -> None:
    rows = [
        _row(
            "R1",
            "A",
            "debit",
            "B",
            "5000.0000",
            1,
            clock="11:00:00",
            reference="R1",
            booked=date(2026, 1, 18),
        ),
        _row(
            "R2",
            "B",
            "debit",
            "A",
            "5000.0000",
            1,
            clock="12:00:00",
            reference="R2",
            booked=date(2026, 1, 18),
        ),
    ]
    result = walk_statements(
        rows,
        start_account_id="A",
        direction="forward",
        max_layer=3,
        currency="INR",
        window_start=date(2026, 1, 18),
        window_end=date(2026, 1, 18),
        amount_min=None,
        amount_max=None,
    )
    assert result.paths[0].stop_reason == "returned_to_earlier_account"
    assert "not a CYCLE finding" in result.limitations
    backward = walk_statements(
        rows,
        start_account_id="B",
        direction="backward",
        max_layer=1,
        currency="INR",
        window_start=date(2026, 1, 18),
        window_end=date(2026, 1, 18),
        amount_min=None,
        amount_max=None,
    )
    assert backward.paths[0].hops[0].from_account_id == "A"


def test_amount_filter_excludes_an_unrelated_transfer() -> None:
    rows = fan_in_rows() + [
        _row("U", "Z", "debit", "Y", "5.0000", 1, reference="U"),
    ]
    result = walk_statements(
        rows,
        start_account_id="100000000021",
        direction="forward",
        max_layer=2,
        currency="INR",
        window_start=D,
        window_end=D,
        amount_min=Decimal("1000.0000"),
        amount_max=None,
    )
    assert all(hop.to_account_id != "Y" for path in result.paths for hop in path.hops)
    assert result.paths[0].hops[0].to_account_id == "100000000030"


def test_repeated_detection_is_stable() -> None:
    kwargs = dict(
        currency="INR",
        window_start=D,
        window_end=D,
        fan_in_min=3,
        fan_out_min=3,
        pass_through_ratio=Decimal("0.85"),
        pass_through_dwell_hours=Decimal(24),
        amount_floor=Decimal("1000.0000"),
    )
    assert detect(fan_in_rows(), **kwargs).output_hash == detect(fan_in_rows(), **kwargs).output_hash
