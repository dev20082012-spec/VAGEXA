import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import { INDICATOR_LABEL, REL_LABEL, formatAmount, formatBooking } from "../../format";
import { ClassBadge, Empty, ErrorBox, Metric, Panel, Skeleton, useLoad } from "../../ui";
import { endpoints } from "./TransactionsView";

export function AccountsView({ caseId }: { caseId: string }) {
  const activity = useLoad(
    () => api.activity(caseId),
    [caseId],
    "Account activity could not be loaded.",
  );
  const indicators = useLoad(() => api.listIndicators(caseId), [caseId]);
  const relationships = useLoad(() => api.relationships(caseId), [caseId]);
  const [selected, setSelected] = useState<string | null>(null);
  const rows = activity.data?.items ?? [];
  const current = rows.find((item) => `${item.account_id}-${item.currency}` === selected) ?? null;
  const history = useLoad(
    () =>
      current
        ? api.transactions(caseId, `?account_id=${current.account_id}&limit=100`)
        : Promise.resolve({ items: [], next_cursor: null }),
    [caseId, current?.account_id],
  );

  return (
    <div className="split">
      <Panel title="Account intelligence" subtitle={activity.data?.comparison}>
        {activity.loading ? <Skeleton lines={6} /> : null}
        {activity.error ? <ErrorBox message={activity.error} onRetry={activity.reload} /> : null}
        {!activity.loading && rows.length === 0 ? (
          <Empty>No statement accounts are loaded.</Empty>
        ) : null}
        {rows.length > 0 ? (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Account</th>
                  <th className="num">In</th>
                  <th className="num">Out</th>
                  <th className="num">Incoming</th>
                  <th className="num">Outgoing</th>
                  <th className="num">Counterparties</th>
                  <th>Period</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((item) => {
                  const key = `${item.account_id}-${item.currency}`;
                  return (
                    <tr
                      key={key}
                      className={`clickable ${key === selected ? "selected" : ""}`}
                      onClick={() => setSelected(key)}
                      tabIndex={0}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") setSelected(key);
                      }}
                    >
                      <td className="mono">{item.account_masked}</td>
                      <td className="num">{item.incoming_count}</td>
                      <td className="num">{item.outgoing_count}</td>
                      <td className="num mono">
                        {formatAmount(item.incoming_amount, item.currency)}
                      </td>
                      <td className="num mono">
                        {formatAmount(item.outgoing_amount, item.currency)}
                      </td>
                      <td className="num">{item.unique_counterparties}</td>
                      <td className="small">
                        {item.period_start} to {item.period_end}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
      </Panel>
      <div className="sticky">
        {!current ? (
          <Panel title="Account detail">
            <Empty>Select an account to see its timeline and related findings.</Empty>
          </Panel>
        ) : (
          <Panel title={current.account_masked ?? "Account"} subtitle={current.coverage}>
            <div className="metrics">
              <Metric label="Incoming rows" value={current.incoming_count} />
              <Metric label="Outgoing rows" value={current.outgoing_count} />
              <Metric label="Counterparties" value={current.unique_counterparties} />
            </div>
            <dl className="kv" style={{ marginTop: 12 }}>
              <dt>Total incoming</dt>
              <dd className="mono">{formatAmount(current.incoming_amount, current.currency)}</dd>
              <dt>Total outgoing</dt>
              <dd className="mono">{formatAmount(current.outgoing_amount, current.currency)}</dd>
              <dt>Median row</dt>
              <dd className="mono">{formatAmount(current.median_amount, current.currency)}</dd>
              <dt>Largest row</dt>
              <dd className="mono">{formatAmount(current.maximum_amount, current.currency)}</dd>
            </dl>
            <hr className="divider" />
            <h3>Timeline</h3>
            {history.loading ? <Skeleton /> : null}
            <ul className="list-plain small">
              {(history.data?.items ?? []).map((row) => {
                const ends = endpoints(row);
                return (
                  <li key={row.id} className="mono">
                    {formatBooking(row.booking_date, row.booking_time)} · {row.direction} ·{" "}
                    {formatAmount(row.amount, row.currency)} · {ends.source} → {ends.destination}
                  </li>
                );
              })}
            </ul>
            <hr className="divider" />
            <h3>Related findings</h3>
            <ul className="list-plain small">
              {(indicators.data?.items ?? [])
                .filter((item) => item.account_id === current.account_id)
                .map((item) => (
                  <li key={item.code}>{INDICATOR_LABEL[item.code] ?? item.code} · rule match</li>
                ))}
              {(relationships.data?.items ?? [])
                .filter(
                  (item) =>
                    item.from_id === current.account_id || item.to_id === current.account_id,
                )
                .filter((item) => item.rel_type !== "same_payment")
                .map((item) => (
                  <li key={item.id}>
                    <Link to={`/cases/${caseId}/unified?rel=${item.id}`}>
                      {REL_LABEL[item.rel_type] ?? item.rel_type}
                    </Link>{" "}
                    <ClassBadge value={item.classification} /> {item.from_label} → {item.to_label}
                  </li>
                ))}
            </ul>
          </Panel>
        )}
      </div>
    </div>
  );
}
