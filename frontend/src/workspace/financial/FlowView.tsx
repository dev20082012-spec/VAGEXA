import { FormEvent, useMemo, useState } from "react";
import { api, errorText } from "../../api/client";
import type { GraphPayload, TraceFlow, TraceResult, WalkResult } from "../../api/types";
import { formatAmount, formatBooking, formatDelay } from "../../format";
import { AssertionBadge, Empty, ErrorBox, Panel, Skeleton, useLoad } from "../../ui";
import { RecordPanel } from "../RecordPanel";
import { useWorkspace } from "../context";

function chain(flows: TraceFlow[]): TraceFlow[] | null {
  const ordered = [...flows].sort((left, right) => left.layer_to - right.layer_to);
  const layers = new Set(ordered.map((item) => item.layer_to));
  return layers.size === ordered.length ? ordered : null;
}

function Hop({
  amount,
  currency,
  booked,
  delay,
  reference,
  onOpen,
  badge,
}: {
  amount: string;
  currency: string;
  booked: string;
  delay: string | null;
  reference: string | null;
  onOpen: () => void;
  badge?: string;
}) {
  return (
    <div className="path-hop">
      <strong>{formatAmount(amount, currency)}</strong>
      <div className="arrow" />
      <span>{booked}</span>
      {formatDelay(delay) ? <span>{formatDelay(delay)}</span> : null}
      <span className="mono">{reference ?? "no reference"}</span>
      {badge ? <span>{badge}</span> : null}
      <button className="link small" type="button" onClick={onOpen}>
        Source record
      </button>
    </div>
  );
}

export function FlowView({ caseId }: { caseId: string }) {
  const { summary, reloadSummary } = useWorkspace();
  const traceId = summary?.latest_trace?.id ?? null;
  const stored = useLoad(
    () => (traceId ? api.getTrace(traceId) : Promise.resolve(null)),
    [traceId],
    "The trace could not be loaded.",
  );
  const [fresh, setFresh] = useState<TraceResult | null>(null);
  const trace = fresh ?? stored.data;
  const [open, setOpen] = useState<string | null>(null);
  const debits = useLoad(() => api.transactions(caseId, "?direction=debit&limit=100"), [caseId]);
  const entities = useLoad(() => api.entities(caseId), [caseId]);
  const [seed, setSeed] = useState("");
  const [horizon, setHorizon] = useState("3");
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [pathFrom, setPathFrom] = useState("");
  const [pathTo, setPathTo] = useState("");
  const [path, setPath] = useState<GraphPayload | null>(null);
  const [pathError, setPathError] = useState<string | null>(null);
  const [walkAccount, setWalkAccount] = useState("");
  const [walkDirection, setWalkDirection] = useState("forward");
  const [walk, setWalk] = useState<WalkResult | null>(null);
  const [walkError, setWalkError] = useState<string | null>(null);

  const ordered = useMemo(() => (trace ? chain(trace.flows) : null), [trace]);
  const accounts = entities.data?.accounts ?? [];

  async function runTrace(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!seed) return;
    setRunning(true);
    setRunError(null);
    try {
      setFresh(await api.trace(caseId, [seed], Number(horizon)));
      reloadSummary();
    } catch (err) {
      setRunError(errorText(err, "The trace did not run."));
    } finally {
      setRunning(false);
    }
  }

  async function findPath(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!pathFrom || !pathTo) return;
    setPathError(null);
    setPath(null);
    try {
      setPath(await api.graph(caseId, `?max_hops=5&path_from=${pathFrom}&path_to=${pathTo}`));
    } catch (err) {
      setPathError(errorText(err, "The path could not be computed."));
    }
  }

  async function runWalk(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!walkAccount) return;
    setWalkError(null);
    setWalk(null);
    try {
      setWalk(await api.walk(caseId, walkAccount, walkDirection));
    } catch (err) {
      setWalkError(errorText(err, "The sequence could not be read."));
    }
  }

  const label = (id: string) => path?.nodes.find((node) => node.id === id)?.label ?? id.slice(0, 8);

  return (
    <div className="split">
      <div className="stack">
        <Panel
          title="Fund-flow allocation"
          subtitle={
            trace
              ? `${trace.method_version}, horizon ${trace.max_layer}, status ${trace.status}`
              : undefined
          }
        >
          {stored.loading && !fresh ? <Skeleton lines={4} /> : null}
          {stored.error ? <ErrorBox message={stored.error} onRetry={stored.reload} /> : null}
          {!trace && !stored.loading ? (
            <Empty>No trace is stored for this case. Run one below.</Empty>
          ) : null}
          {trace ? (
            <>
              <p className="notice">
                {trace.path_summary?.note ?? "Each hop is an allocation under fifo.v1."} A path is
                not proof that the same funds moved through every account.
              </p>
              {ordered && ordered.length > 0 ? (
                <div className="path" aria-label="Allocated path">
                  <div className="path-node">
                    <span className="mono">{ordered[0].from_account_masked}</span>
                    <span className="small muted">origin</span>
                  </div>
                  {ordered.map((flow) => {
                    const holding = trace.residuals.some(
                      (item) => item.account_masked === flow.to_account_masked,
                    );
                    return (
                      <div
                        key={`${flow.layer_to}-${flow.source_transaction_id}`}
                        style={{ display: "contents" }}
                      >
                        <Hop
                          amount={flow.amount}
                          currency={flow.currency}
                          booked={formatBooking(flow.booking_date, flow.booking_time)}
                          delay={flow.hours_after_previous}
                          reference={flow.reference}
                          badge={`layer ${flow.layer_to} · ${flow.assertion_kind}`}
                          onOpen={() => setOpen(flow.source_transaction_id)}
                        />
                        <div className={`path-node ${holding ? "holding" : ""}`}>
                          <span className="mono">{flow.to_account_masked ?? flow.exit_kind}</span>
                          <span className="small muted">
                            {holding ? "holds the residual" : `layer ${flow.layer_to}`}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : null}
              {trace.flows.length > 0 && !ordered ? (
                <table className="table">
                  <thead>
                    <tr>
                      <th>Layer</th>
                      <th>From</th>
                      <th>To</th>
                      <th className="num">Amount</th>
                      <th>Booked</th>
                      <th>Record</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trace.flows.map((flow) => (
                      <tr key={`${flow.layer_to}-${flow.source_transaction_id}-${flow.amount}`}>
                        <td>{flow.layer_to}</td>
                        <td className="mono">{flow.from_account_masked}</td>
                        <td className="mono">{flow.to_account_masked ?? flow.exit_kind}</td>
                        <td className="num mono">{formatAmount(flow.amount, flow.currency)}</td>
                        <td className="small">
                          {formatBooking(flow.booking_date, flow.booking_time)}
                        </td>
                        <td>
                          <button
                            className="link"
                            type="button"
                            onClick={() => setOpen(flow.source_transaction_id)}
                          >
                            Open
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : null}
              {trace.flows.length === 0 ? (
                <Empty>The run published no flows. {trace.error_code ?? ""}</Empty>
              ) : null}
              {trace.residuals.map((item) => (
                <p key={`${item.account_masked}-${item.reason}`} className="notice caution">
                  {formatAmount(item.amount, item.currency)} remains on{" "}
                  <span className="mono">{item.account_masked}</span> as{" "}
                  <strong>{item.reason}</strong>. This account is not an attributed beneficiary.
                </p>
              ))}
              <p className="muted small">{trace.limitations}</p>
            </>
          ) : null}
        </Panel>
        <Panel
          title="Run a new trace"
          subtitle="Stores a new analytical run. The statement rows are not changed."
        >
          <form className="toolbar" onSubmit={runTrace}>
            <label className="field">
              Seed payment
              <select value={seed} onChange={(event) => setSeed(event.target.value)} required>
                <option value="">Choose an outgoing payment</option>
                {(debits.data?.items ?? []).map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.booking_date} {row.account_masked} → {row.counterparty_masked}{" "}
                    {formatAmount(row.amount, row.currency)} {row.source_transaction_id ?? ""}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Horizon
              <select value={horizon} onChange={(event) => setHorizon(event.target.value)}>
                {["1", "2", "3", "4", "5"].map((value) => (
                  <option key={value} value={value}>
                    {value} hops
                  </option>
                ))}
              </select>
            </label>
            <button className="primary" type="submit" disabled={running || !seed}>
              {running ? "Tracing…" : "Run fifo.v1"}
            </button>
          </form>
          {runError ? <ErrorBox message={runError} /> : null}
        </Panel>
        <Panel
          title="Path between two accounts"
          subtitle="Shortest directed path over stored transfers, at most 5 hops. This is an observed sequence, not an allocation."
        >
          <form className="toolbar" onSubmit={findPath}>
            <label className="field">
              From
              <select value={pathFrom} onChange={(event) => setPathFrom(event.target.value)}>
                <option value="">Account</option>
                {accounts.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.masked}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              To
              <select value={pathTo} onChange={(event) => setPathTo(event.target.value)}>
                <option value="">Account</option>
                {accounts.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.masked}
                  </option>
                ))}
              </select>
            </label>
            <button className="quiet" type="submit" disabled={!pathFrom || !pathTo}>
              Find path
            </button>
          </form>
          {pathError ? <ErrorBox message={pathError} /> : null}
          {path && !path.path ? <Empty>No path: {path.path_reason}.</Empty> : null}
          {path?.path ? (
            <div className="path">
              {path.path.map((nodeId, index) => {
                const nextId = path.path?.[index + 1];
                const edge = nextId
                  ? path.edges.find(
                      (item) =>
                        item.kind === "transfer" && item.from === nodeId && item.to === nextId,
                    )
                  : undefined;
                return (
                  <div key={nodeId} style={{ display: "contents" }}>
                    <div className="path-node">
                      <span className="mono">{label(nodeId)}</span>
                    </div>
                    {edge ? (
                      <Hop
                        amount={edge.amount}
                        currency={edge.currency}
                        booked={edge.booking_date ?? "—"}
                        delay={null}
                        reference={null}
                        badge={edge.method_name}
                        onOpen={() => setOpen(edge.source_transaction_ids[0] ?? null)}
                      />
                    ) : null}
                  </div>
                );
              })}
            </div>
          ) : null}
        </Panel>
        <Panel
          title="Observed sequence"
          subtitle="statement_walk.v1. Forward or backward over verified statement transfers."
        >
          <form className="toolbar" onSubmit={runWalk}>
            <label className="field">
              Account
              <select value={walkAccount} onChange={(event) => setWalkAccount(event.target.value)}>
                <option value="">Account</option>
                {accounts.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.masked}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Direction
              <select
                value={walkDirection}
                onChange={(event) => setWalkDirection(event.target.value)}
              >
                <option value="forward">Forward: where it paid</option>
                <option value="backward">Backward: who paid it</option>
              </select>
            </label>
            <button className="quiet" type="submit" disabled={!walkAccount}>
              Read sequence
            </button>
          </form>
          {walkError ? <ErrorBox message={walkError} /> : null}
          {walk ? (
            <>
              <p className="muted small">{walk.limitations}</p>
              {walk.paths.every((item) => item.hops.length === 0) ? (
                <Empty>No further statement hop.</Empty>
              ) : null}
              <ul className="list-plain small">
                {walk.paths
                  .filter((item) => item.hops.length > 0)
                  .map((item, index) => (
                    <li key={`${item.stop_reason}-${index}`} className="mono">
                      {item.hops
                        .map(
                          (hop) =>
                            `${hop.from_account_masked} → ${hop.to_account_masked} ${formatAmount(hop.amount, "INR")}`,
                        )
                        .join("  ·  ")}
                      <span className="muted"> · stop: {item.stop_reason}</span>
                    </li>
                  ))}
              </ul>
            </>
          ) : null}
        </Panel>
      </div>
      <div className="sticky">
        <Panel title="Source record" subtitle="The statement row behind the selected hop">
          {open ? (
            <RecordPanel caseId={caseId} kind="transaction" objectId={open} />
          ) : (
            <Empty>Select a hop.</Empty>
          )}
          {trace ? (
            <div className="small muted" style={{ marginTop: 10 }}>
              Hop assertions:{" "}
              {Array.from(new Set(trace.flows.map((flow) => flow.assertion_kind))).map((kind) => (
                <AssertionBadge key={kind} value={kind} />
              ))}
            </div>
          ) : null}
        </Panel>
      </div>
    </div>
  );
}
