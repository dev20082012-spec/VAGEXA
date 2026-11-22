"""fifo.v1 against the synthetic chain. Ground truth is the validation scenario, not the detector."""

from datetime import date, time
from decimal import Decimal

from vagexa.intelligence.financial.fifo import Flow, Seed, trace
from vagexa.intelligence.financial.ledger import LedgerRow

D = date(2026, 1, 15)
ACCOUNTS = {"100000000001", "100000000011", "100000000012", "100000000013", "100000000019"}


def _row(
    row_id: str,
    account: str,
    direction: str,
    counterparty: str,
    reference: str,
    clock: str | None,
    line: int,
    amount: str = "100000.0000",
    booked: date = D,
    rail: str = "imps",
    resolution: str = "structured_field",
    currency: str = "INR",
) -> LedgerRow:
    return LedgerRow(
        id=row_id,
        account_id=account,
        direction=direction,
        amount=Decimal(amount),
        currency=currency,
        booking_date=booked,
        booking_time=time.fromisoformat(clock) if clock else None,
        line_number=line,
        counterparty_account_id=counterparty,
        counterparty_resolution=resolution,
        reference=reference,
        rail=rail,
        time_precision="time" if clock else "date",
    )


def scenario_one() -> list[LedgerRow]:
    return [
        _row("V", "100000000001", "debit", "100000000011", "UTRSYN0001", "09:00:00", 1),
        _row("I1C", "100000000011", "credit", "100000000001", "UTRSYN0001", "09:01:00", 1),
        _row("I1D", "100000000011", "debit", "100000000012", "UTRSYN0002", "09:20:00", 2),
        _row("I2C", "100000000012", "credit", "100000000011", "UTRSYN0002", "09:21:00", 1),
        _row("I2D", "100000000012", "debit", "100000000013", "UTRSYN0003", "10:00:00", 2),
        _row("I3C", "100000000013", "credit", "100000000012", "UTRSYN0003", "10:01:00", 1),
        _row("I3D", "100000000013", "debit", "100000000019", "UTRSYN0004", "11:00:00", 2),
        _row("BC", "100000000019", "credit", "100000000013", "UTRSYN0004", "11:01:00", 1),
    ]


def _hops(flows: list[Flow]) -> list[tuple[str, str | None, int, str]]:
    return [(item.from_account_id, item.to_account_id, item.layer_to, f"{item.amount:.4f}") for item in flows]


def test_horizon_three_stops_before_the_final_account() -> None:
    result = trace(scenario_one(), [Seed("V")], max_layer=3, currency="INR", statement_account_ids=ACCOUNTS)
    assert result.status == "succeeded"
    assert _hops(result.flows) == [
        ("100000000001", "100000000011", 1, "100000.0000"),
        ("100000000011", "100000000012", 2, "100000.0000"),
        ("100000000012", "100000000013", 3, "100000.0000"),
    ]
    assert all(
        item.assertion_kind == "verified" and item.method_name == "reference_join" for item in result.flows
    )
    assert [(item.account_id, item.reason, f"{item.amount:.4f}") for item in result.residuals] == [
        ("100000000013", "outside_horizon", "100000.0000")
    ]
    assert all(item.to_account_id != "100000000019" for item in result.flows)
    assert "outside_horizon is not an attributed beneficiary" in result.limitations
    assert sum((item.amount for item in result.flows), Decimal("0")) == Decimal("300000.0000")


def test_horizon_four_includes_the_named_beneficiary() -> None:
    result = trace(scenario_one(), [Seed("V")], max_layer=4, currency="INR", statement_account_ids=ACCOUNTS)
    assert [item.to_account_id for item in result.flows][-1] == "100000000019"
    assert result.residuals == []


def test_the_same_input_has_the_same_output_hash() -> None:
    first = trace(scenario_one(), [Seed("V")], max_layer=3, currency="INR", statement_account_ids=ACCOUNTS)
    second = trace(scenario_one(), [Seed("V")], max_layer=3, currency="INR", statement_account_ids=ACCOUNTS)
    assert first.output_hash == second.output_hash
    assert first.output_hash is not None


def test_null_times_follow_line_number() -> None:
    rows = [
        _row("C1", "A", "credit", "S", "R1", None, 1, "50.0000", resolution="structured_field"),
        _row("C2", "A", "credit", "T", "R2", None, 2, "70.0000"),
        _row("D", "A", "debit", "B", "R3", None, 3, "50.0000"),
    ]
    result = trace(
        rows,
        [Seed("C1", "first"), Seed("C2", "second")],
        max_layer=3,
        currency="INR",
        statement_account_ids={"A", "B"},
    )
    assert len(result.flows) == 1
    assert result.flows[0].complaint_id == "first"
    assert result.flows[0].amount == Decimal("50.0000")
    assert "file order" in result.limitations


def test_reversal_with_the_same_reference_nets() -> None:
    debit = _row("D", "A", "debit", "B", "SAME", "09:00:00", 1, "100.0000")
    credit = _row("C", "A", "credit", "B", "SAME", "09:05:00", 2, "100.0000")
    netted = trace(
        [debit, credit], [Seed("D")], max_layer=3, currency="INR", statement_account_ids={"A", "B"}
    )
    assert netted.flows == []
    other = _row("C2", "A", "credit", "B", "OTHER", "09:05:00", 2, "100.0000")
    kept = trace([debit, other], [Seed("D")], max_layer=3, currency="INR", statement_account_ids={"A", "B"})
    assert len(kept.flows) == 1
    assert kept.flows[0].amount == Decimal("100.0000")


def test_a_larger_debit_emits_only_the_attributed_part() -> None:
    rows = [
        _row("C", "A", "credit", "S", "IN", "09:00:00", 1, "40.0000"),
        _row("D", "A", "debit", "B", "OUT", "10:00:00", 2, "100.0000"),
    ]
    result = trace(rows, [Seed("C")], max_layer=3, currency="INR", statement_account_ids={"A", "B"})
    assert [(f"{item.amount:.4f}", item.to_account_id) for item in result.flows] == [("40.0000", "B")]


def test_unrelated_same_amount_is_not_one_path() -> None:
    rows = scenario_one() + [
        _row("U1", "100000000041", "debit", "100000000042", "UNREL", "12:00:00", 1, "100000.0000"),
        _row("U2", "100000000042", "credit", "100000000041", "UNREL", "12:01:00", 1, "100000.0000"),
    ]
    result = trace(
        rows,
        [Seed("V")],
        max_layer=3,
        currency="INR",
        statement_account_ids=ACCOUNTS | {"100000000041", "100000000042"},
    )
    assert all(item.from_account_id not in {"100000000041", "100000000042"} for item in result.flows)
    assert _hops(result.flows)[0][0] == "100000000001"


def test_missing_destination_statement_is_a_residual_not_extra_money() -> None:
    rows = [_row("V", "100000000001", "debit", "100000000011", "UTRSYN0001", "09:00:00", 1)]
    result = trace(rows, [Seed("V")], max_layer=3, currency="INR", statement_account_ids={"100000000001"})
    assert result.flows[0].to_account_id == "100000000011"
    assert result.residuals[0].reason == "no_onward_record"
    assert result.residuals[0].amount == result.flows[0].amount


def test_cash_exit_invents_no_account() -> None:
    rows = [_row("V", "A", "debit", "B", "CASH", "09:00:00", 1, "10.0000", rail="cash")]
    result = trace(rows, [Seed("V")], max_layer=3, currency="INR", statement_account_ids={"A", "B"})
    assert result.flows[0].to_account_id is None
    assert result.flows[0].exit_kind == "cash"


def test_conservation_fault_publishes_nothing() -> None:
    result = trace(
        scenario_one(),
        [Seed("V")],
        max_layer=3,
        currency="INR",
        statement_account_ids=ACCOUNTS,
        fault_extra_outflow=Decimal("1.0000"),
    )
    assert result.status == "failed"
    assert result.error_code == "conservation"
    assert result.flows == []
    assert result.residuals == []


def test_decimal_split_stays_exact() -> None:
    rows = [
        _row("C", "A", "credit", "S", "IN", "09:00:00", 1, "0.3000"),
        _row("D1", "A", "debit", "B", "O1", "10:00:00", 2, "0.1000"),
        _row("D2", "A", "debit", "C", "O2", "11:00:00", 3, "0.2000"),
    ]
    result = trace(rows, [Seed("C")], max_layer=3, currency="INR", statement_account_ids={"A", "B", "C"})
    assert [f"{item.amount:.4f}" for item in result.flows] == ["0.1000", "0.2000"]


def test_other_currency_is_not_allocated() -> None:
    rows = scenario_one() + [
        _row("FX", "100000000001", "debit", "100000000099", "USD1", "08:00:00", 2, "5.0000", currency="USD")
    ]
    result = trace(rows, [Seed("V")], max_layer=3, currency="INR", statement_account_ids=ACCOUNTS)
    assert all(item.currency == "INR" for item in result.flows)
    assert len(result.flows) == 3


def test_a_long_chain_does_not_walk_past_the_horizon() -> None:
    import time as clock

    rows = []
    accounts: set[str] = set()
    for index in range(3000):
        source = f"A{index}"
        dest = f"A{index + 1}"
        accounts.update({source, dest})
        rows.append(_row(f"T{index}", source, "debit", dest, f"R{index}", "09:00:00", 1, "1.0000"))
    started = clock.perf_counter()
    result = trace(rows, [Seed("T0")], max_layer=3, currency="INR", statement_account_ids=accounts)
    elapsed = clock.perf_counter() - started
    assert elapsed < 2
    assert len(result.flows) == 3
    assert result.residuals[0].account_id == "A3"
    assert result.residuals[0].reason == "outside_horizon"


def test_branching_keeps_both_destinations() -> None:
    rows = [
        _row("V", "V", "debit", "A", "S", "09:00:00", 1, "100.0000"),
        _row("A1", "A", "debit", "B", "B", "10:00:00", 1, "60.0000"),
        _row("A2", "A", "debit", "C", "C", "11:00:00", 2, "40.0000"),
    ]
    result = trace(rows, [Seed("V")], max_layer=3, currency="INR", statement_account_ids={"V", "A", "B", "C"})
    assert sorted(
        (item.to_account_id, f"{item.amount:.4f}") for item in result.flows if item.layer_to == 2
    ) == [
        ("B", "60.0000"),
        ("C", "40.0000"),
    ]
