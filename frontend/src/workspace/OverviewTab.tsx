import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { InvestigationSummary } from "../api/types";
import { INDICATOR_LABEL, REL_LABEL, formatAmount, formatDateTime } from "../format";
import { ClassBadge, Empty, ErrorBox, Metric, Panel, Skeleton, StatusBadge, useLoad } from "../ui";
import { useWorkspace } from "./context";

function narrative(summary: InvestigationSummary): string[] {
  const lines: string[] = [];
  const { counts } = summary;
  lines.push(
    `${counts.statements} statements are loaded, containing ${counts.transactions} transaction rows.`,
  );
  const trace = summary.latest_trace;
  if (trace) {
    const residual = trace.residuals[0];
    lines.push(
      `A ${trace.method_version} trace at horizon ${trace.max_layer ?? "?"} published ${trace.flow_count} allocated hops` +
        (residual
          ? `. ${formatAmount(residual.amount, residual.currency)} remains on ${residual.account_masked} as ${residual.reason}.`
          : "."),
    );
  } else {
    lines.push("No fund-flow trace has been run.");
  }
  for (const item of summary.indicators) {
    lines.push(
      `Rule ${item.code} matched on ${item.account_masked}, citing ${item.support_count} transactions.`,
    );
  }
  lines.push(
    `${counts.dns_observations} DNS observations, ${counts.hosting_observations} hosting notes, and ${counts.gateway_records} payment-gateway records are stored.`,
  );
  for (const item of summary.key_relationships.filter(
    (row) => row.rel_type === "gateway_merchant",
  )) {
    lines.push(
      `A gateway record links ${item.from_label} to ${item.to_label}. Classification ${item.classification}, review status ${item.status}.`,
    );
  }
  return lines;
}

function openQuestions(summary: InvestigationSummary): string[] {
  const questions: string[] = [];
  for (const residual of summary.latest_trace?.residuals ?? []) {
    if (residual.reason === "outside_horizon") {
      questions.push(
        `Where did the value held by ${residual.account_masked} go after the trace horizon?`,
      );
    }
    if (residual.reason === "no_onward_record") {
      questions.push(`No statement is loaded for ${residual.account_masked}. Request it.`);
    }
  }
  const proposed = summary.key_relationships.filter((row) => row.status === "proposed").length;
  if (proposed) {
    questions.push(
      `${proposed} cross-domain or infrastructure relationships await an investigator decision.`,
    );
  }
  if (summary.relationships_by_classification.UNRESOLVED) {
    questions.push(
      "Shared infrastructure is unresolved. Who operates each domain is not established.",
    );
  }
  if (summary.relationships_by_classification.CONTRADICTED) {
    questions.push(
      `${summary.relationships_by_classification.CONTRADICTED} relationships are contradicted. The disagreeing source records are both still stored.`,
    );
  }
  questions.push("Domain registration and certificate data are not collected in this deployment.");
  return questions;
}

export function OverviewTab() {
  const { caseId, summary, summaryError, reloadSummary } = useWorkspace();
  const entities = useLoad(() => api.entities(caseId), [caseId], "Entities could not be loaded.");

  if (summaryError) return <ErrorBox message={summaryError} onRetry={reloadSummary} />;
  if (!summary) return <Skeleton lines={6} />;

  const subjects = (entities.data?.accounts ?? [])
    .filter((item) => item.role === "statement_subject")
    .sort((left, right) => right.statement_rows - left.statement_rows);

  return (
    <div className="stack">
      <div className="metrics">
        <Metric label="Transactions" value={summary.counts.transactions} />
        <Metric label="Statements" value={summary.counts.statements} />
        <Metric
          label="Accounts cited"
          value={entities.data ? entities.data.accounts.length : "…"}
        />
        <Metric label="Domains" value={entities.data ? entities.data.domains.length : "…"} />
        <Metric
          label="IP addresses"
          value={entities.data ? entities.data.ip_addresses.length : "…"}
        />
        <Metric label="Gateway records" value={summary.counts.gateway_records} />
        <Metric label="Findings" value={summary.counts.findings} />
        <Metric label="Relationships" value={summary.counts.relationships} />
      </div>
      <div className="grid-2">
        <Panel
          title="Case narrative"
          subtitle="Assembled from stored records and analytical results"
        >
          <p>
            <strong>Objective.</strong> {summary.case.title}
          </p>
          <ul>
            {narrative(summary).map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          <p className="notice caution">{summary.limitations}</p>
        </Panel>
        <Panel title="Open questions" subtitle="Derived from what is and is not stored">
          <ul>
            {openQuestions(summary).map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </Panel>
      </div>
      <div className="grid-3">
        <Panel
          title="Fund flow"
          actions={<Link to={`/cases/${caseId}/financial?view=flow`}>Open</Link>}
        >
          {summary.latest_trace ? (
            <>
              <p>
                {summary.latest_trace.method_version}, horizon {summary.latest_trace.max_layer},{" "}
                {summary.latest_trace.flow_count} allocated hops.
              </p>
              {summary.latest_trace.residuals.map((item) => (
                <p key={`${item.account_masked}-${item.reason}`} className="small">
                  Residual <span className="mono">{formatAmount(item.amount, item.currency)}</span>{" "}
                  on <span className="mono">{item.account_masked}</span>: {item.reason}. Not an
                  attributed beneficiary.
                </p>
              ))}
            </>
          ) : (
            <Empty>No trace has been run.</Empty>
          )}
        </Panel>
        <Panel
          title="Transaction patterns"
          actions={<Link to={`/cases/${caseId}/financial?view=findings`}>Open</Link>}
        >
          {summary.indicators.length === 0 ? (
            <Empty>No rule matched in the latest run.</Empty>
          ) : null}
          <ul className="list-plain">
            {summary.indicators.map((item) => (
              <li key={`${item.code}-${item.account_masked}`}>
                <strong>{INDICATOR_LABEL[item.code] ?? item.code}</strong>
                <div className="small muted">
                  <span className="mono">{item.account_masked}</span> · {item.support_count}{" "}
                  supporting rows · rule match
                </div>
              </li>
            ))}
          </ul>
        </Panel>
        <Panel
          title="Cross-domain links"
          actions={<Link to={`/cases/${caseId}/unified`}>Open</Link>}
        >
          {summary.key_relationships.length === 0 ? (
            <Empty>No relationship has been proposed.</Empty>
          ) : null}
          <ul className="list-plain">
            {summary.key_relationships.map((item) => (
              <li key={item.id}>
                <Link to={`/cases/${caseId}/unified?rel=${item.id}`}>
                  {REL_LABEL[item.rel_type] ?? item.rel_type}
                </Link>
                <div className="small">
                  <span className="mono">{item.from_label}</span> →{" "}
                  <span className="mono">{item.to_label}</span>{" "}
                  <ClassBadge value={item.classification} /> <StatusBadge value={item.status} />
                </div>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
      <div className="grid-2">
        <Panel title="Key entities" subtitle={entities.data?.note}>
          {entities.error ? <ErrorBox message={entities.error} onRetry={entities.reload} /> : null}
          {entities.loading ? <Skeleton /> : null}
          {entities.data ? (
            <div className="grid-2">
              <div>
                <h3>Statement accounts</h3>
                <ul className="list-plain small">
                  {subjects.slice(0, 8).map((item) => (
                    <li key={item.id} className="mono">
                      {item.masked} · {item.statement_rows} rows
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h3>Infrastructure</h3>
                <ul className="list-plain small">
                  {entities.data.domains.map((item) => (
                    <li key={item.id} className="mono">
                      {item.name} · {item.dns_observations} DNS
                      {item.in_gateway_record ? " · in gateway record" : ""}
                    </li>
                  ))}
                  {entities.data.ip_addresses.map((item) => (
                    <li key={item.id} className="mono">
                      {item.address}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ) : null}
        </Panel>
        <Panel title="Recent activity" subtitle="Audit actions on this case">
          {summary.recent_activity.length === 0 ? <Empty>No activity recorded.</Empty> : null}
          <table className="table">
            <tbody>
              {summary.recent_activity.map((item, index) => (
                <tr key={`${item.occurred_at}-${item.action}-${index}`}>
                  <td className="mono small">{formatDateTime(item.occurred_at)}</td>
                  <td>{item.action}</td>
                  <td>{item.outcome}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      </div>
    </div>
  );
}
