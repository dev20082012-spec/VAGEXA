import { api } from "../api/client";
import { INDICATOR_LABEL, REL_LABEL, formatAmount, formatBooking, formatDateTime } from "../format";
import { ErrorBox, Skeleton, useLoad } from "../ui";
import { useWorkspace } from "./context";

export function ReportTab() {
  const { caseId, record, summary, summaryError } = useWorkspace();
  const traceId = summary?.latest_trace?.id ?? null;
  const trace = useLoad(() => (traceId ? api.getTrace(traceId) : Promise.resolve(null)), [traceId]);
  const entities = useLoad(() => api.entities(caseId), [caseId]);
  const indicators = useLoad(() => api.listIndicators(caseId), [caseId]);
  const relationships = useLoad(() => api.relationships(caseId), [caseId]);
  const observations = useLoad(() => api.observations(caseId), [caseId]);
  const gateway = useLoad(() => api.gatewayRecords(caseId), [caseId]);

  if (summaryError) return <ErrorBox message={summaryError} />;
  const loading =
    !summary ||
    trace.loading ||
    entities.loading ||
    indicators.loading ||
    relationships.loading ||
    observations.loading;
  if (loading) return <Skeleton lines={10} />;

  const cross = (relationships.data?.items ?? []).filter(
    (item) => item.rel_type !== "same_payment",
  );
  const pairs = (relationships.data?.items ?? []).filter(
    (item) => item.rel_type === "same_payment",
  ).length;
  const subjects = (entities.data?.accounts ?? []).filter(
    (item) => item.role === "statement_subject",
  );

  return (
    <article className="panel report">
      <div className="panel-head no-print">
        <p className="muted small">
          Generated in the browser from the stored case. Use print to save a PDF.
        </p>
        <button className="primary" type="button" onClick={() => window.print()}>
          Print or save as PDF
        </button>
      </div>
      <header style={{ marginBottom: 18 }}>
        <div className="mono muted">{record.reference}</div>
        <h1>{record.title}</h1>
        <p className="muted small">
          Classification {record.data_classification} · opened {record.opened_on} · report generated{" "}
          {formatDateTime(new Date().toISOString())}
        </p>
        {summary.synthetic_notice ? <p className="synthetic">{summary.synthetic_notice}</p> : null}
      </header>

      <section>
        <h2>1. Overview</h2>
        <p>
          This report lists the stored records of the case and the analytical results computed from
          them. Observed records and analytical results are listed separately. No section is a
          finding of guilt, ownership, or identity.
        </p>
      </section>

      <section>
        <h2>2. Scope of data analysed</h2>
        <ul>
          <li>
            {summary.counts.statements} statements, {summary.counts.transactions} transaction rows.
          </li>
          <li>
            {summary.counts.dns_observations} DNS observations,{" "}
            {summary.counts.hosting_observations} hosting notes, {summary.counts.gateway_records}{" "}
            payment-gateway records.
          </li>
          <li>Registration, certificate, ASN, and live DNS data were not collected.</li>
        </ul>
      </section>

      <section>
        <h2>3. Financial entities (observed)</h2>
        <table className="table">
          <thead>
            <tr>
              <th>Account</th>
              <th className="num">Statement rows</th>
            </tr>
          </thead>
          <tbody>
            {subjects.map((item) => (
              <tr key={item.id}>
                <td className="mono">{item.masked}</td>
                <td className="num">{item.statement_rows}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="muted small">{entities.data?.note}</p>
      </section>

      <section>
        <h2>4. Detected patterns (analytical)</h2>
        {(indicators.data?.items ?? []).length === 0 ? <p>No indicator rule matched.</p> : null}
        <ul>
          {(indicators.data?.items ?? []).map((item) => (
            <li key={`${item.code}-${item.account_id}`}>
              <strong>{INDICATOR_LABEL[item.code] ?? item.code}</strong> on{" "}
              <span className="mono">{item.account_masked}</span>,{" "}
              {item.support_transaction_ids.length} supporting rows, {item.method_version}.{" "}
              {item.limitations}
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2>5. Fund-flow analysis (analytical)</h2>
        {!trace.data ? <p>No trace was run.</p> : null}
        {trace.data ? (
          <>
            <p>
              {trace.data.method_version}, horizon {trace.data.max_layer}. Output hash{" "}
              <span className="mono">{trace.data.output_hash?.slice(0, 16) ?? "—"}</span>.
            </p>
            <table className="table">
              <thead>
                <tr>
                  <th>Layer</th>
                  <th>From</th>
                  <th>To</th>
                  <th className="num">Allocated</th>
                  <th>Booked</th>
                  <th>Reference</th>
                </tr>
              </thead>
              <tbody>
                {trace.data.flows.map((flow) => (
                  <tr key={`${flow.layer_to}-${flow.source_transaction_id}`}>
                    <td>{flow.layer_to}</td>
                    <td className="mono">{flow.from_account_masked}</td>
                    <td className="mono">{flow.to_account_masked ?? flow.exit_kind}</td>
                    <td className="num mono">{formatAmount(flow.amount, flow.currency)}</td>
                    <td className="small">{formatBooking(flow.booking_date, flow.booking_time)}</td>
                    <td className="mono small">{flow.reference ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {trace.data.residuals.map((item) => (
              <p key={`${item.account_masked}-${item.reason}`}>
                Residual {formatAmount(item.amount, item.currency)} on{" "}
                <span className="mono">{item.account_masked}</span>: {item.reason}. Not an
                attributed beneficiary.
              </p>
            ))}
            <p className="muted small">{trace.data.limitations}</p>
          </>
        ) : null}
      </section>

      <section>
        <h2>6. Digital infrastructure (observed)</h2>
        <table className="table">
          <thead>
            <tr>
              <th>Observed</th>
              <th>Domain</th>
              <th>Answer</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {(observations.data?.dns ?? []).map((row) => (
              <tr key={row.id}>
                <td className="small mono">{formatDateTime(row.observed_at)}</td>
                <td className="mono">{row.domain}</td>
                <td className="mono">
                  {row.rrtype} {row.rdata}
                </td>
                <td>{row.resolver}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="muted small">{observations.data?.limitation}</p>
      </section>

      <section>
        <h2>7. Cross-domain relationships (analytical proposals)</h2>
        {cross.length === 0 ? <p>None proposed.</p> : null}
        <table className="table">
          <thead>
            <tr>
              <th>Rule</th>
              <th>From</th>
              <th>To</th>
              <th>Classification</th>
              <th>Review</th>
            </tr>
          </thead>
          <tbody>
            {cross.map((item) => (
              <tr key={item.id}>
                <td>{REL_LABEL[item.rel_type] ?? item.rel_type}</td>
                <td className="mono">{item.from_label}</td>
                <td className="mono">{item.to_label}</td>
                <td>{item.classification}</td>
                <td>{item.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="muted small">
          {pairs} statement pairs that share a payment reference are not listed.
        </p>
      </section>

      <section>
        <h2>8. Supporting evidence (observed)</h2>
        <ul>
          {(gateway.data?.items ?? []).map((item) => (
            <li key={item.object_id}>
              Gateway record <span className="mono">{String(item.record.source_record_id)}</span>{" "}
              from {String(item.record.source_system)}: reference{" "}
              <span className="mono">{String(item.record.payment_reference)}</span>, settlement
              account <span className="mono">{String(item.record.payee_account_masked)}</span>,
              merchant <span className="mono">{String(item.record.merchant_domain)}</span>,
              processed {formatDateTime(item.time.value)}.
            </li>
          ))}
          <li>
            Statement rows and DNS observations are listed in sections 3, 5, and 6, and in the
            Evidence tab with provenance.
          </li>
        </ul>
      </section>

      <section>
        <h2>9. Analytical limitations</h2>
        <p>{summary.limitations}</p>
        <ul>
          {cross.map((item) => (
            <li key={item.id}>{item.limitation}</li>
          ))}
        </ul>
      </section>

      <section>
        <h2>10. Unresolved questions</h2>
        <ul>
          {(summary.latest_trace?.residuals ?? []).map((item) => (
            <li key={`${item.account_masked}-${item.reason}`}>
              Where did the value on <span className="mono">{item.account_masked}</span> go beyond
              the trace horizon?
            </li>
          ))}
          {cross
            .filter((item) => item.status === "proposed")
            .map((item) => (
              <li key={item.id}>
                Decide the proposed {REL_LABEL[item.rel_type]?.toLowerCase() ?? item.rel_type}{" "}
                between <span className="mono">{item.from_label}</span> and{" "}
                <span className="mono">{item.to_label}</span>.
              </li>
            ))}
          <li>Who registered and operates each domain is not established.</li>
        </ul>
      </section>
    </article>
  );
}
