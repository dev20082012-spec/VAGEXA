import { useEffect } from "react";
import { Link, NavLink, Outlet, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { formatDateTime } from "../format";
import { DEMO_REFERENCE, GUIDE, guideHref } from "../guide";
import { ErrorBox, Skeleton, StatusBadge, SyntheticNotice, useLoad } from "../ui";
import { CASE_EVENT, type WorkspaceContext } from "./context";

export const TABS = [
  { path: "", label: "Overview" },
  { path: "financial", label: "Financial intelligence" },
  { path: "network", label: "Network explorer" },
  { path: "infrastructure", label: "Infrastructure" },
  { path: "unified", label: "Unified intelligence" },
  { path: "evidence", label: "Evidence" },
  { path: "report", label: "Report" },
];

export function WorkspaceLayout() {
  const { caseId = "" } = useParams();
  const [params] = useSearchParams();
  const record = useLoad(() => api.case(caseId), [caseId], "This investigation is not available.");
  const summary = useLoad(() => api.summary(caseId), [caseId], "The summary could not be loaded.");

  useEffect(() => {
    if (record.data) {
      window.dispatchEvent(
        new CustomEvent(CASE_EVENT, {
          detail: { id: record.data.id, reference: record.data.reference },
        }),
      );
    }
  }, [record.data]);

  if (record.loading && !record.data) {
    return <Skeleton lines={4} />;
  }
  if (record.error || !record.data) {
    return (
      <div className="stack">
        <ErrorBox message={record.error ?? "This investigation is not available."} />
        <p>
          <Link to="/cases">Back to investigations</Link>
        </p>
      </div>
    );
  }

  const step = Number(params.get("guide") || "0");
  const showGuide = record.data.reference === DEMO_REFERENCE && step >= 1 && step <= GUIDE.length;
  const lastActivity = summary.data?.recent_activity[0]?.occurred_at;
  const context: WorkspaceContext = {
    caseId,
    record: record.data,
    summary: summary.data,
    summaryError: summary.error,
    reloadSummary: summary.reload,
  };

  return (
    <>
      {showGuide ? (
        <div className="guide" role="region" aria-label="Guided walkthrough">
          <div>
            <strong>
              Step {step} of {GUIDE.length}: {GUIDE[step - 1].title}
            </strong>
            <div className="small">{GUIDE[step - 1].text}</div>
          </div>
          <div className="actions">
            {step > 1 ? (
              <Link className="button quiet" to={guideHref(caseId, step - 1)}>
                Back
              </Link>
            ) : null}
            {step < GUIDE.length ? (
              <Link className="button" to={guideHref(caseId, step + 1)}>
                Next
              </Link>
            ) : (
              <Link className="button" to={`/cases/${caseId}/report`}>
                Finish
              </Link>
            )}
            <Link to={`/cases/${caseId}`}>Exit walkthrough</Link>
          </div>
        </div>
      ) : null}
      <header className="workspace-header">
        <div className="workspace-title">
          <div>
            <div className="mono muted">{record.data.reference}</div>
            <h1>{record.data.title}</h1>
            <div className="workspace-meta">
              <span>
                Status <StatusBadge value={record.data.status} />
              </span>
              <span>Opened {record.data.opened_on}</span>
              <span>
                Last activity {lastActivity ? formatDateTime(lastActivity) : "none recorded"}
              </span>
              <span>
                Classification{" "}
                <span
                  className={`badge ${record.data.data_classification === "synthetic" ? "synthetic" : "neutral"}`}
                >
                  {record.data.data_classification}
                </span>
              </span>
            </div>
          </div>
          {record.data.reference === DEMO_REFERENCE && !showGuide ? (
            <Link className="button quiet no-print" to={guideHref(caseId, 1)}>
              Guided walkthrough
            </Link>
          ) : null}
        </div>
        <nav className="tabs" aria-label="Investigation sections">
          {TABS.map((tab) => (
            <NavLink
              key={tab.label}
              to={`/cases/${caseId}${tab.path ? `/${tab.path}` : ""}`}
              end={tab.path === ""}
            >
              {tab.label}
            </NavLink>
          ))}
        </nav>
      </header>
      {record.data.data_classification === "synthetic" ? (
        <SyntheticNotice text={summary.data?.synthetic_notice} />
      ) : null}
      <Outlet context={context} />
    </>
  );
}
