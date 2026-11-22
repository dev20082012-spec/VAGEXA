import { FormEvent, useEffect, useState } from "react";
import { api, errorText } from "../../api/client";
import { INDICATOR_LABEL } from "../../format";
import { AssertionBadge, Empty, ErrorBox, Panel, Skeleton, useLoad } from "../../ui";
import { RecordPanel } from "../RecordPanel";

const KIND_TITLE: Record<string, string> = {
  trace: "Fund-flow allocation",
  indicator: "Indicator rule",
  statement_walk: "Observed sequence",
  correlation: "Correlation proposal",
};

export function FindingsView({ caseId }: { caseId: string }) {
  const indicators = useLoad(
    () => api.listIndicators(caseId),
    [caseId],
    "Indicator results could not be loaded.",
  );
  const findings = useLoad(() => api.findings(caseId), [caseId], "Findings could not be loaded.");
  const [open, setOpen] = useState<string | null>(null);
  const [windowStart, setWindowStart] = useState("");
  const [windowEnd, setWindowEnd] = useState("");
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  useEffect(() => {
    const stored = indicators.data?.parameters;
    if (!stored) return;
    setWindowStart((value) => value || String(stored.window_start ?? ""));
    setWindowEnd((value) => value || String(stored.window_end ?? ""));
  }, [indicators.data]);

  async function rerun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRunning(true);
    setRunError(null);
    try {
      await api.indicators(caseId, windowStart, windowEnd);
      indicators.reload();
      findings.reload();
    } catch (err) {
      setRunError(errorText(err, "The rules did not run."));
    } finally {
      setRunning(false);
    }
  }

  const other = (findings.data?.items ?? []).filter((item) => item.finding_kind !== "indicator");
  const parameters = indicators.data?.parameters;

  return (
    <div className="split">
      <div className="stack">
        <Panel
          title="Pattern findings"
          subtitle="indicators.v1 on verified structured-field transfers. There is no severity score: each row is a rule match."
        >
          {indicators.loading ? <Skeleton lines={4} /> : null}
          {indicators.error ? (
            <ErrorBox message={indicators.error} onRetry={indicators.reload} />
          ) : null}
          {parameters ? (
            <p className="muted small">
              Window {String(parameters.window_start)} to {String(parameters.window_end)} · fan-in
              at least {String(parameters.fan_in_min)} · fan-out at least{" "}
              {String(parameters.fan_out_min)} · pass-through ratio{" "}
              {String(parameters.pass_through_ratio)}. Demonstration settings, not legal thresholds.
            </p>
          ) : null}
          {indicators.data && indicators.data.items.length === 0 ? (
            <Empty>
              {indicators.data.run_id
                ? "No rule matched in the latest run."
                : "No indicator run is stored."}
            </Empty>
          ) : null}
          {(indicators.data?.items ?? []).map((item) => (
            <div key={`${item.code}-${item.account_id}`} className="record-card">
              <div className="panel-head">
                <div>
                  <h3>{INDICATOR_LABEL[item.code] ?? item.code}</h3>
                  <p className="muted small">
                    Account <span className="mono">{item.account_masked}</span> ·{" "}
                    {item.method_version}
                  </p>
                </div>
                <div className="actions">
                  <AssertionBadge value={item.assertion_kind} />
                  <span className="badge neutral">Not scored</span>
                </div>
              </div>
              <p className="small">{item.limitations}</p>
              <p className="small">
                Supporting transactions ({item.support_transaction_ids.length}):{" "}
                {item.support_transaction_ids.map((id) => (
                  <button
                    key={id}
                    className="link mono"
                    type="button"
                    onClick={() => setOpen(id)}
                    style={{ marginRight: 8 }}
                  >
                    {id.slice(0, 8)}
                  </button>
                ))}
              </p>
            </div>
          ))}
        </Panel>
        <Panel
          title="Other analytical results"
          subtitle="Stored findings with their method and limitations"
        >
          {findings.loading ? <Skeleton /> : null}
          {findings.error ? <ErrorBox message={findings.error} onRetry={findings.reload} /> : null}
          {findings.data && other.length === 0 ? (
            <Empty>No other findings are stored.</Empty>
          ) : null}
          <div className="table-wrap">
            <table className="table">
              <tbody>
                {other.slice(0, 40).map((item) => (
                  <tr key={item.id}>
                    <td>
                      <strong>{KIND_TITLE[item.finding_kind] ?? item.finding_kind}</strong>
                      <div className="small">{item.summary}</div>
                      <div className="muted small">{item.limitations}</div>
                    </td>
                    <td className="small">
                      <AssertionBadge value={item.assertion_kind} />
                      <div className="muted mono">{item.method_version}</div>
                    </td>
                    <td className="small">
                      {item.support_transaction_ids.length} rows
                      {item.support_transaction_ids[0] ? (
                        <div>
                          <button
                            className="link"
                            type="button"
                            onClick={() => setOpen(item.support_transaction_ids[0])}
                          >
                            Open first
                          </button>
                        </div>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
        <Panel title="Re-run indicator rules" subtitle="Stores a new run with these parameters.">
          <form className="toolbar" onSubmit={rerun}>
            <label className="field">
              Window start
              <input
                type="date"
                value={windowStart}
                onChange={(event) => setWindowStart(event.target.value)}
                required
              />
            </label>
            <label className="field">
              Window end
              <input
                type="date"
                value={windowEnd}
                onChange={(event) => setWindowEnd(event.target.value)}
                required
              />
            </label>
            <button className="quiet" type="submit" disabled={running}>
              {running ? "Running…" : "Run indicators.v1"}
            </button>
          </form>
          {runError ? <ErrorBox message={runError} /> : null}
        </Panel>
      </div>
      <div className="sticky">
        <Panel title="Supporting record">
          {open ? (
            <RecordPanel caseId={caseId} kind="transaction" objectId={open} />
          ) : (
            <Empty>Select a supporting row.</Empty>
          )}
        </Panel>
      </div>
    </div>
  );
}
