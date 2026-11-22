import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, errorText } from "../../api/client";
import type { FindingRow, RelationshipRow, TransactionRow } from "../../api/types";
import { REL_LABEL, compareAmount, formatAmount, formatBooking } from "../../format";
import { ClassBadge, Empty, ErrorBox, Panel, Skeleton, useLoad } from "../../ui";
import { supportedGateway } from "../../selection";
import { RecordPanel } from "../RecordPanel";

type Filters = {
  direction: string;
  currency: string;
  dateFrom: string;
  dateTo: string;
  amountMin: string;
  amountMax: string;
  accountId: string;
};

const EMPTY: Filters = {
  direction: "",
  currency: "",
  dateFrom: "",
  dateTo: "",
  amountMin: "",
  amountMax: "",
  accountId: "",
};

function query(filters: Filters, offset: string | null): string {
  const params = new URLSearchParams({ limit: "50" });
  if (filters.direction) params.set("direction", filters.direction);
  if (filters.currency) params.set("currency", filters.currency);
  if (filters.dateFrom) params.set("booking_date_from", filters.dateFrom);
  if (filters.dateTo) params.set("booking_date_to", filters.dateTo);
  if (filters.amountMin) params.set("amount_min", filters.amountMin);
  if (filters.amountMax) params.set("amount_max", filters.amountMax);
  if (filters.accountId) params.set("account_id", filters.accountId);
  if (offset) params.set("offset", offset);
  return `?${params.toString()}`;
}

export function endpoints(row: TransactionRow): { source: string; destination: string } {
  const own = row.account_masked ?? "—";
  const other = row.counterparty_masked ?? (row.rail === "cash" ? "cash" : "unresolved");
  return row.direction === "debit"
    ? { source: own, destination: other }
    : { source: other, destination: own };
}

export function TransactionsView({ caseId }: { caseId: string }) {
  const [params] = useSearchParams();
  const [draft, setDraft] = useState<Filters>(EMPTY);
  const [filters, setFilters] = useState<Filters>(EMPTY);
  const [rows, setRows] = useState<TransactionRow[]>([]);
  const [next, setNext] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<"date" | "amount">("date");
  const [selected, setSelected] = useState<string | null>(null);
  const entities = useLoad(() => api.entities(caseId), [caseId]);
  const relationships = useLoad(() => api.relationships(caseId), [caseId]);
  const findings = useLoad(() => api.findings(caseId), [caseId]);

  useEffect(() => {
    let live = true;
    setLoading(true);
    setError(null);
    api
      .transactions(caseId, query(filters, null))
      .then((body) => {
        if (!live) return;
        setRows(body.items);
        setNext(body.next_cursor);
      })
      .catch((err: unknown) => {
        if (live) setError(errorText(err, "Transactions could not be loaded."));
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
  }, [caseId, filters]);

  useEffect(() => {
    if (params.get("focus") !== "bridge" || selected || !relationships.data || rows.length === 0)
      return;
    const bridge = supportedGateway(relationships.data.items);
    const ids = new Set(
      bridge?.support
        .filter((item) => item.object_kind === "transaction")
        .map((item) => item.object_id),
    );
    const debit = rows.find((row) => ids.has(row.id) && row.direction === "debit");
    if (debit) setSelected(debit.id);
  }, [params, relationships.data, rows, selected]);

  async function loadMore() {
    if (!next) return;
    setLoading(true);
    try {
      const body = await api.transactions(caseId, query(filters, next));
      setRows((current) => [...current, ...body.items]);
      setNext(body.next_cursor);
    } catch (err) {
      setError(errorText(err, "The next page could not be loaded."));
    } finally {
      setLoading(false);
    }
  }

  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase();
    const filtered = needle
      ? rows.filter((row) =>
          [
            row.reference_raw,
            row.source_transaction_id,
            row.account_masked,
            row.counterparty_masked,
          ]
            .filter(Boolean)
            .some((value) => String(value).toLowerCase().includes(needle)),
        )
      : rows;
    if (sort === "amount")
      return [...filtered].sort((left, right) => compareAmount(right.amount, left.amount));
    return filtered;
  }, [rows, search, sort]);

  const subjects = (entities.data?.accounts ?? []).filter(
    (item) => item.role === "statement_subject",
  );
  const selectedRow = rows.find((row) => row.id === selected) ?? null;

  return (
    <div className="split">
      <Panel
        title="Transaction explorer"
        subtitle="Statement rows stored for this case. Only posted rows are ingested."
      >
        <div className="toolbar">
          <label className="field">
            Account
            <select
              value={draft.accountId}
              onChange={(event) => setDraft({ ...draft, accountId: event.target.value })}
            >
              <option value="">All accounts</option>
              {subjects.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.masked}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Direction
            <select
              value={draft.direction}
              onChange={(event) => setDraft({ ...draft, direction: event.target.value })}
            >
              <option value="">Both</option>
              <option value="debit">Outgoing (debit)</option>
              <option value="credit">Incoming (credit)</option>
            </select>
          </label>
          <label className="field">
            Currency
            <input
              size={4}
              value={draft.currency}
              onChange={(event) =>
                setDraft({ ...draft, currency: event.target.value.toUpperCase() })
              }
            />
          </label>
          <label className="field">
            From
            <input
              type="date"
              value={draft.dateFrom}
              onChange={(event) => setDraft({ ...draft, dateFrom: event.target.value })}
            />
          </label>
          <label className="field">
            To
            <input
              type="date"
              value={draft.dateTo}
              onChange={(event) => setDraft({ ...draft, dateTo: event.target.value })}
            />
          </label>
          <label className="field">
            Min amount
            <input
              size={9}
              value={draft.amountMin}
              onChange={(event) => setDraft({ ...draft, amountMin: event.target.value })}
            />
          </label>
          <label className="field">
            Max amount
            <input
              size={9}
              value={draft.amountMax}
              onChange={(event) => setDraft({ ...draft, amountMax: event.target.value })}
            />
          </label>
          <div className="actions">
            <button className="primary" type="button" onClick={() => setFilters(draft)}>
              Apply
            </button>
            <button
              className="quiet"
              type="button"
              onClick={() => {
                setDraft(EMPTY);
                setFilters(EMPTY);
              }}
            >
              Clear
            </button>
          </div>
        </div>
        <div className="toolbar">
          <label className="field">
            Search loaded rows
            <input
              placeholder="Reference, source id, or ****1234"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
          <label className="field">
            Sort
            <select
              value={sort}
              onChange={(event) => setSort(event.target.value as "date" | "amount")}
            >
              <option value="date">Booking date</option>
              <option value="amount">Amount, largest first</option>
            </select>
          </label>
          <span className="muted small">
            {visible.length} of {rows.length} loaded{next ? ", more available" : ""}
          </span>
        </div>
        {error ? <ErrorBox message={error} onRetry={() => setFilters({ ...filters })} /> : null}
        {loading && rows.length === 0 ? <Skeleton lines={6} /> : null}
        {!loading && !error && rows.length === 0 ? (
          <Empty>No transactions match these filters.</Empty>
        ) : null}
        {visible.length > 0 ? (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Booked</th>
                  <th>From</th>
                  <th>To</th>
                  <th className="num">Amount</th>
                  <th>Reference</th>
                  <th>Rail</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((row) => {
                  const ends = endpoints(row);
                  return (
                    <tr
                      key={row.id}
                      className={`clickable ${row.id === selected ? "selected" : ""}`}
                      onClick={() => setSelected(row.id)}
                      tabIndex={0}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") setSelected(row.id);
                      }}
                    >
                      <td className="mono small">
                        {formatBooking(row.booking_date, row.booking_time)}
                      </td>
                      <td className="mono">{ends.source}</td>
                      <td className="mono">{ends.destination}</td>
                      <td className="num mono">{formatAmount(row.amount, row.currency)}</td>
                      <td className="mono small">{row.reference_raw ?? "—"}</td>
                      <td>{row.rail}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
        {next ? (
          <p>
            <button
              className="quiet"
              type="button"
              onClick={() => void loadMore()}
              disabled={loading}
            >
              {loading ? "Loading…" : "Load the next page"}
            </button>
          </p>
        ) : null}
      </Panel>
      <div className="sticky">
        {selectedRow ? (
          <TransactionDetail
            caseId={caseId}
            row={selectedRow}
            relationships={relationships.data?.items ?? []}
            findings={findings.data?.items ?? []}
            onClose={() => setSelected(null)}
          />
        ) : (
          <Panel title="Transaction detail">
            <Empty>Select a row to open its source record and provenance.</Empty>
          </Panel>
        )}
      </div>
    </div>
  );
}

function TransactionDetail({
  caseId,
  row,
  relationships,
  findings,
  onClose,
}: {
  caseId: string;
  row: TransactionRow;
  relationships: RelationshipRow[];
  findings: FindingRow[];
  onClose: () => void;
}) {
  const ends = endpoints(row);
  const linked = relationships.filter((item) =>
    item.support.some((support) => support.object_id === row.id),
  );
  const cited = findings.filter((item) => item.support_transaction_ids.includes(row.id));
  return (
    <Panel
      title={formatAmount(row.amount, row.currency)}
      subtitle={`${ends.source} → ${ends.destination}`}
      actions={
        <button className="quiet" type="button" onClick={onClose}>
          Back to list
        </button>
      }
    >
      <RecordPanel caseId={caseId} kind="transaction" objectId={row.id} />
      <hr className="divider" />
      <h3>Analytical results citing this row</h3>
      {linked.length === 0 && cited.length === 0 ? (
        <p className="muted small">No relationship or finding cites this row.</p>
      ) : null}
      <ul className="list-plain small">
        {linked.map((item) => (
          <li key={item.id}>
            <Link to={`/cases/${caseId}/unified?rel=${item.id}`}>
              {REL_LABEL[item.rel_type] ?? item.rel_type}
            </Link>{" "}
            <ClassBadge value={item.classification} />
            <div className="muted">
              {item.from_label} → {item.to_label}
            </div>
          </li>
        ))}
        {cited.map((item) => (
          <li key={item.id}>
            Finding: {item.finding_kind} · {item.method_version}
          </li>
        ))}
      </ul>
    </Panel>
  );
}
