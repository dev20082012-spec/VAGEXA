import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "./api/client";
import type { CaseRecord, InvestigationSummary } from "./api/types";
import { INDICATOR_LABEL, formatDateTime } from "./format";
import { DEMO_REFERENCE, guideHref } from "./guide";
import { ClassBadge, Empty, ErrorBox, Metric, Panel, Skeleton, StatusBadge, useLoad } from "./ui";

const SUMMARY_LIMIT = 12;

type Overview = { cases: CaseRecord[]; summaries: Record<string, InvestigationSummary> };

async function loadOverview(): Promise<Overview> {
  const { items } = await api.cases();
  const results = await Promise.allSettled(
    items.slice(0, SUMMARY_LIMIT).map((item) => api.summary(item.id)),
  );
  const summaries: Record<string, InvestigationSummary> = {};
  results.forEach((result, index) => {
    if (result.status === "fulfilled") summaries[items[index].id] = result.value;
  });
  return { cases: items, summaries };
}

/** Cross-domain links only. Statement pairs that share a reference are not counted here. */
function supported(summary: InvestigationSummary): number {
  const counts = summary.cross_domain_by_classification;
  return (counts.DIRECTLY_SUPPORTED ?? 0) + (counts.CORROBORATED ?? 0);
}

export function DashboardPage() {
  const overview = useLoad(loadOverview, [], "The investigations could not be loaded.");
  const data = overview.data;
  const summaries = useMemo(() => Object.values(data?.summaries ?? {}), [data]);
  const demo = data?.cases.find((item) => item.reference === DEMO_REFERENCE) ?? null;
  const demoSummary = demo ? data?.summaries[demo.id] : undefined;
  const totals = useMemo(
    () => ({
      transactions: summaries.reduce((sum, item) => sum + item.counts.transactions, 0),
      infrastructure: summaries.reduce(
        (sum, item) => sum + item.counts.dns_observations + item.counts.hosting_observations,
        0,
      ),
      candidates: summaries.reduce(
        (sum, item) =>
          sum +
          Object.values(item.cross_domain_by_classification).reduce((a, b) => a + b, 0) +
          item.overlap_count,
        0,
      ),
      supported: summaries.reduce((sum, item) => sum + supported(item), 0),
      unresolved: summaries.reduce(
        (sum, item) => sum + (item.relationships_by_classification.UNRESOLVED ?? 0),
        0,
      ),
    }),
    [summaries],
  );
  const activity = useMemo(
    () =>
      Object.entries(data?.summaries ?? {})
        .flatMap(([id, item]) =>
          item.recent_activity.map((row) => ({
            ...row,
            caseId: id,
            reference: item.case.reference,
          })),
        )
        .sort((left, right) => right.occurred_at.localeCompare(left.occurred_at))
        .slice(0, 8),
    [data],
  );

  return (
    <div className="stack">
      <div className="page-header">
        <div>
          <h1>Overview</h1>
          <p className="lede">
            VAGEXA connects bank statement records with domain and address observations, and shows
            which links the stored evidence supports. Figures below are counts of stored rows in the
            investigations assigned to you.
          </p>
        </div>
      </div>
      {overview.error ? <ErrorBox message={overview.error} onRetry={overview.reload} /> : null}
      {overview.loading ? <Skeleton lines={5} /> : null}
      {data ? (
        <>
          {demo ? (
            <Panel
              title={
                <>
                  Demonstration investigation <span className="badge synthetic">Synthetic</span>
                </>
              }
              subtitle={`${demo.reference} · ${demo.title}`}
              actions={
                <>
                  <Link className="button" to={guideHref(demo.id, 1)}>
                    Start the guided walkthrough
                  </Link>
                  <Link className="button quiet" to={`/cases/${demo.id}`}>
                    Open the investigation
                  </Link>
                </>
              }
            >
              {demoSummary ? (
                <div className="metrics">
                  <Metric label="Transactions" value={demoSummary.counts.transactions} />
                  <Metric
                    label="Allocated hops"
                    value={demoSummary.latest_trace?.flow_count ?? 0}
                  />
                  <Metric label="Rule matches" value={demoSummary.indicators.length} />
                  <Metric
                    label="Infrastructure observations"
                    value={
                      demoSummary.counts.dns_observations + demoSummary.counts.hosting_observations
                    }
                  />
                  <Metric label="Supported cross-domain links" value={supported(demoSummary)} />
                  <Metric label="Unresolved overlaps" value={demoSummary.overlap_count} />
                </div>
              ) : (
                <p className="muted">The summary for this investigation is not available.</p>
              )}
            </Panel>
          ) : (
            <p className="notice caution">
              The {DEMO_REFERENCE} demonstration investigation is not assigned to you or has not
              been loaded.
            </p>
          )}
          <div className="metrics">
            <Metric label="Investigations" value={data.cases.length} />
            <Metric
              label="Open"
              value={data.cases.filter((item) => item.status === "open").length}
            />
            <Metric label="Transactions analysed" value={totals.transactions} />
            <Metric label="Infrastructure observations" value={totals.infrastructure} />
            <Metric label="Correlation candidates" value={totals.candidates} />
            <Metric label="Supported relationships" value={totals.supported} />
            <Metric label="Unresolved relationships" value={totals.unresolved} />
          </div>
          {data.cases.length > SUMMARY_LIMIT ? (
            <p className="muted small">Totals cover the first {SUMMARY_LIMIT} investigations.</p>
          ) : null}
          <div className="grid-2">
            <Panel
              title="Important findings"
              subtitle="Rule matches and supported cross-domain links, from stored results"
            >
              {summaries.every(
                (item) => item.indicators.length === 0 && item.key_relationships.length === 0,
              ) ? (
                <Empty>No finding is stored yet.</Empty>
              ) : null}
              <ul className="list-plain small">
                {Object.entries(data.summaries).flatMap(([id, item]) => [
                  ...item.indicators.map((row) => (
                    <li key={`${id}-${row.code}-${row.account_masked}`}>
                      <Link to={`/cases/${id}/financial?view=findings`}>
                        {INDICATOR_LABEL[row.code] ?? row.code}
                      </Link>{" "}
                      on <span className="mono">{row.account_masked}</span>
                      <span className="muted"> · {item.case.reference} · rule match</span>
                    </li>
                  )),
                  ...item.key_relationships
                    .filter((row) => row.rel_type === "gateway_merchant")
                    .map((row) => (
                      <li key={`${id}-${row.id}`}>
                        <Link to={`/cases/${id}/unified?rel=${row.id}`}>
                          Gateway settlement link
                        </Link>{" "}
                        <span className="mono">{row.from_label}</span> →{" "}
                        <span className="mono">{row.to_label}</span>{" "}
                        <ClassBadge value={row.classification} />
                        <span className="muted"> · {item.case.reference}</span>
                      </li>
                    )),
                ])}
              </ul>
            </Panel>
            <Panel title="Recent activity" subtitle="Audit actions across your investigations">
              {activity.length === 0 ? <Empty>No activity recorded.</Empty> : null}
              <table className="table">
                <tbody>
                  {activity.map((row, index) => (
                    <tr key={`${row.caseId}-${row.occurred_at}-${row.action}-${index}`}>
                      <td className="mono small">{formatDateTime(row.occurred_at)}</td>
                      <td>
                        <Link to={`/cases/${row.caseId}`}>{row.reference}</Link>
                      </td>
                      <td>{row.action}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Panel>
          </div>
          <InvestigationList cases={data.cases} summaries={data.summaries} />
        </>
      ) : null}
    </div>
  );
}

export function InvestigationsPage() {
  const overview = useLoad(loadOverview, [], "The investigations could not be loaded.");
  return (
    <div className="stack">
      <div className="page-header">
        <div>
          <h1>Investigations</h1>
          <p className="lede">
            Investigations assigned to you. Synthetic investigations are labelled.
          </p>
        </div>
      </div>
      {overview.error ? <ErrorBox message={overview.error} onRetry={overview.reload} /> : null}
      {overview.loading ? <Skeleton lines={5} /> : null}
      {overview.data ? (
        <InvestigationList cases={overview.data.cases} summaries={overview.data.summaries} />
      ) : null}
    </div>
  );
}

function InvestigationList({
  cases,
  summaries,
}: {
  cases: CaseRecord[];
  summaries: Record<string, InvestigationSummary>;
}) {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [sort, setSort] = useState<"activity" | "opened" | "reference">("activity");
  const needle = search.trim().toLowerCase();
  const rows = cases
    .filter((item) => status === "all" || item.status === status)
    .filter(
      (item) =>
        !needle ||
        item.reference.toLowerCase().includes(needle) ||
        item.title.toLowerCase().includes(needle),
    )
    .map((item) => ({
      item,
      summary: summaries[item.id],
      last: summaries[item.id]?.recent_activity[0]?.occurred_at ?? "",
    }))
    .sort((left, right) => {
      if (sort === "reference") return left.item.reference.localeCompare(right.item.reference);
      if (sort === "opened") return right.item.opened_on.localeCompare(left.item.opened_on);
      return right.last.localeCompare(left.last);
    });

  return (
    <Panel title="Investigation register">
      <div className="toolbar">
        <label className="field">
          Search
          <input
            value={search}
            placeholder="Reference or title"
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <label className="field">
          Status
          <select value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="all">All</option>
            <option value="open">Open</option>
            <option value="closed">Closed</option>
          </select>
        </label>
        <label className="field">
          Sort
          <select value={sort} onChange={(event) => setSort(event.target.value as typeof sort)}>
            <option value="activity">Last activity</option>
            <option value="opened">Opened, newest first</option>
            <option value="reference">Reference</option>
          </select>
        </label>
      </div>
      {rows.length === 0 ? <Empty>No investigation matches.</Empty> : null}
      {rows.length > 0 ? (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Reference</th>
                <th>Title</th>
                <th>Status</th>
                <th>Opened</th>
                <th>Last activity</th>
                <th className="num">Transactions</th>
                <th className="num">Relationships</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ item, summary, last }) => (
                <tr key={item.id}>
                  <td className="mono">
                    <Link to={`/cases/${item.id}`}>{item.reference}</Link>{" "}
                    {item.data_classification === "synthetic" ? (
                      <span className="badge synthetic">Synthetic</span>
                    ) : null}
                  </td>
                  <td>{item.title}</td>
                  <td>
                    <StatusBadge value={item.status} />
                  </td>
                  <td className="mono small">{item.opened_on}</td>
                  <td className="mono small">{last ? formatDateTime(last) : "—"}</td>
                  <td className="num">{summary ? summary.counts.transactions : "—"}</td>
                  <td className="num">{summary ? summary.counts.relationships : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </Panel>
  );
}
