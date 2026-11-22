import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, errorText } from "../api/client";
import type { RelationshipRow } from "../api/types";
import {
  CLASS_TEXT,
  KIND_LABEL,
  REL_LABEL,
  RULE_GUIDANCE,
  formatBooking,
  formatDateTime,
} from "../format";
import {
  AssertionBadge,
  ClassBadge,
  Empty,
  ErrorBox,
  Metric,
  Panel,
  Skeleton,
  SourceRecordView,
  StatusBadge,
  useLoad,
} from "../ui";
import { supportedGateway } from "../selection";
import { useWorkspace } from "./context";

const ORDER = [
  "DIRECTLY_SUPPORTED",
  "CORROBORATED",
  "INFERRED",
  "HYPOTHESIS",
  "UNRESOLVED",
  "CONTRADICTED",
];

function entity(row: RelationshipRow, side: "from" | "to") {
  const kind = side === "from" ? row.from_kind : row.to_kind;
  const value = side === "from" ? row.from_label : row.to_label;
  return (
    <>
      <span className="mono">{value ?? "—"}</span>
      <div className="muted small">{KIND_LABEL[kind] ?? kind}</div>
    </>
  );
}

export function UnifiedTab() {
  const { caseId, reloadSummary } = useWorkspace();
  const [params, setParams] = useSearchParams();
  const relationships = useLoad(
    () => api.relationships(caseId),
    [caseId],
    "Relationships could not be loaded.",
  );
  const [showPairs, setShowPairs] = useState(false);
  const [running, setRunning] = useState(false);
  const [runMessage, setRunMessage] = useState<string | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const items = useMemo(() => relationships.data?.items ?? [], [relationships.data]);
  const selectedId = params.get("rel");

  useEffect(() => {
    if (selectedId || items.length === 0) return;
    const preferred =
      supportedGateway(items) ?? items.find((item) => item.rel_type !== "same_payment");
    if (preferred) {
      const next = new URLSearchParams(params);
      next.set("rel", preferred.id);
      setParams(next, { replace: true });
    }
  }, [items, params, selectedId, setParams]);

  function select(id: string) {
    const next = new URLSearchParams(params);
    next.set("rel", id);
    next.delete("focus");
    setParams(next);
  }

  async function run() {
    setRunning(true);
    setRunError(null);
    setRunMessage(null);
    try {
      const body = await api.correlate(caseId);
      setRunMessage(
        `${body.inserted} new proposals. ${body.already_present} were already stored and were not duplicated.`,
      );
      relationships.reload();
      reloadSummary();
    } catch (err) {
      setRunError(errorText(err, "Correlation did not run."));
    } finally {
      setRunning(false);
    }
  }

  const visible = useMemo(
    () => items.filter((item) => showPairs || item.rel_type !== "same_payment"),
    [items, showPairs],
  );
  const counts = useMemo(() => {
    const result: Record<string, number> = {};
    for (const item of visible) {
      const key = item.classification ?? "UNCLASSIFIED";
      result[key] = (result[key] ?? 0) + 1;
    }
    return result;
  }, [visible]);
  const crossDomain = items.filter(
    (item) => item.from_kind === "account" && item.to_kind !== "account",
  ).length;
  const selected = items.find((item) => item.id === selectedId) ?? null;

  return (
    <div className="stack">
      <div className="metrics">
        <Metric label="Cross-domain links" value={crossDomain} />
        {ORDER.map((key) => (
          <Metric key={key} label={key.replace("_", " ").toLowerCase()} value={counts[key] ?? 0} />
        ))}
      </div>
      <div className="split">
        <Panel
          title="Correlation explorer"
          subtitle="correlate.v2 proposes a link only when a stored key matches. Time alone creates nothing."
          actions={
            <button className="quiet" type="button" onClick={() => void run()} disabled={running}>
              {running ? "Running…" : "Re-run correlation"}
            </button>
          }
        >
          {runMessage ? <p className="notice">{runMessage}</p> : null}
          {runError ? <ErrorBox message={runError} /> : null}
          <label className="check" style={{ marginBottom: 10 }}>
            <input
              type="checkbox"
              checked={showPairs}
              onChange={(event) => setShowPairs(event.target.checked)}
            />
            Include statement pairs that share a payment reference
          </label>
          {relationships.loading ? <Skeleton lines={5} /> : null}
          {relationships.error ? (
            <ErrorBox message={relationships.error} onRetry={relationships.reload} />
          ) : null}
          {relationships.data && visible.length === 0 ? (
            <Empty>
              No relationship has been proposed. Run correlation after loading statements and
              observations.
            </Empty>
          ) : null}
          {visible.length > 0 ? (
            <div className="table-wrap">
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
                  {visible.map((item) => (
                    <tr
                      key={item.id}
                      className={`clickable ${item.id === selectedId ? "selected" : ""}`}
                      onClick={() => select(item.id)}
                      tabIndex={0}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") select(item.id);
                      }}
                    >
                      <td>{REL_LABEL[item.rel_type] ?? item.rel_type}</td>
                      <td>{entity(item, "from")}</td>
                      <td>{entity(item, "to")}</td>
                      <td>
                        <ClassBadge value={item.classification} />
                      </td>
                      <td>
                        <StatusBadge value={item.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </Panel>
        <div className="sticky">
          {selected ? (
            <RelationshipDetail
              key={selected.id}
              row={selected}
              onDecided={() => {
                relationships.reload();
                reloadSummary();
              }}
            />
          ) : (
            <Panel title="Relationship detail">
              <Empty>Select a relationship.</Empty>
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
}

function RelationshipDetail({ row, onDecided }: { row: RelationshipRow; onDecided: () => void }) {
  const evidence = useLoad(
    () => api.relationshipEvidence(row.id),
    [row.id],
    "Supporting records could not be loaded.",
  );
  const [note, setNote] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const guidance = RULE_GUIDANCE[row.rel_type];

  async function decide(decision: "confirm" | "reject") {
    setPending(true);
    setError(null);
    try {
      await api.reviewRelationship(row.id, decision, note);
      setNote("");
      onDecided();
    } catch (err) {
      setError(errorText(err, "The review was not stored."));
    } finally {
      setPending(false);
    }
  }

  return (
    <Panel
      title={REL_LABEL[row.rel_type] ?? row.rel_type}
      subtitle={`${row.from_label ?? "—"} → ${row.to_label ?? "—"}`}
      actions={<ClassBadge value={row.classification} />}
    >
      <h3>Why this relationship exists</h3>
      <p>{row.claim ?? row.explanation}</p>
      <p className="small muted">{row.classification ? CLASS_TEXT[row.classification] : null}</p>
      <dl className="kv small">
        <dt>Matching rule</dt>
        <dd className="mono">
          {row.rel_type} · {row.method_version}
        </dd>
        <dt>Stored assertion</dt>
        <dd>
          <AssertionBadge value={row.assertion_kind} /> for the stated claim only
        </dd>
        <dt>Review status</dt>
        <dd>
          <StatusBadge value={row.status} />
        </dd>
        <dt>Time context</dt>
        <dd>
          {row.temporal_context.length === 0 ? "None stored." : null}
          {row.temporal_context.map((item) => (
            <div key={`${item.object_kind}-${item.object_id}`}>
              {KIND_LABEL[item.object_kind] ?? item.object_kind}:{" "}
              {item.field === "booking_date"
                ? `${formatBooking(item.value, item.clock)} (statement clock, no time zone)`
                : formatDateTime(item.value)}
            </div>
          ))}
        </dd>
      </dl>
      <p className="notice caution small" style={{ marginTop: 10 }}>
        {row.limitation}
      </p>
      <h3>Supporting source records ({row.support.length})</h3>
      {evidence.loading ? <Skeleton lines={4} /> : null}
      {evidence.error ? <ErrorBox message={evidence.error} onRetry={evidence.reload} /> : null}
      {(evidence.data?.items ?? []).map((item) => (
        <SourceRecordView
          key={`${item.object_kind}-${item.object_id}`}
          item={item}
          showOriginal={false}
        />
      ))}
      <h3 style={{ marginTop: 12 }}>Contradicting evidence</h3>
      <p className="small">
        {row.classification === "CONTRADICTED"
          ? "Another stored record ties the same payment to a different domain. Both are kept."
          : "No contradicting record is stored for this relationship."}
      </p>
      {guidance ? (
        <>
          <h3>Guidance for this rule</h3>
          <p className="muted small">
            General guidance written for the rule. It is not a finding about this case.
          </p>
          {guidance.missing.length ? (
            <>
              <strong className="small">Evidence still missing</strong>
              <ul className="small">
                {guidance.missing.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </>
          ) : null}
          <strong className="small">Alternative explanations</strong>
          <ul className="small">
            {guidance.alternatives.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          <strong className="small">What to verify</strong>
          <ul className="small">
            {guidance.verify.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </>
      ) : null}
      <hr className="divider" />
      <h3>Investigator review</h3>
      {row.reviews.map((item) => (
        <p key={`${item.created_at}-${item.decision}`} className="small">
          <StatusBadge value={item.decision} /> {item.reason}{" "}
          <span className="muted">{formatDateTime(item.created_at)}</span>
        </p>
      ))}
      {row.status === "proposed" ? (
        <>
          <label className="field">
            Reasoning
            <textarea rows={3} value={note} onChange={(event) => setNote(event.target.value)} />
          </label>
          <div className="actions">
            <button
              className="primary"
              type="button"
              disabled={pending}
              onClick={() => void decide("confirm")}
            >
              Accept as working link
            </button>
            <button
              className="quiet"
              type="button"
              disabled={pending}
              onClick={() => {
                if (window.confirm("Reject this proposal? The row and your reason are kept."))
                  void decide("reject");
              }}
            >
              Reject
            </button>
          </div>
          <p className="muted small">
            Accepting does not change the assertion kind or any source record.
          </p>
        </>
      ) : (
        <p className="muted small">This decision is stored. The source records were not changed.</p>
      )}
      {error ? <ErrorBox message={error} /> : null}
    </Panel>
  );
}
