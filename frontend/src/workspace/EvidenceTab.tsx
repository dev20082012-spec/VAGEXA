import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import {
  KIND_LABEL,
  REL_LABEL,
  formatAmount,
  formatBooking,
  formatDateTime,
  shortId,
} from "../format";
import { ClassBadge, Empty, ErrorBox, Panel, Skeleton, useLoad } from "../ui";
import { RecordPanel } from "./RecordPanel";
import { supportedGateway } from "../selection";
import { useWorkspace } from "./context";

type Item = { kind: string; id: string; label: string; time: string; classification: string };

export function EvidenceTab() {
  const { caseId } = useWorkspace();
  const [params] = useSearchParams();
  const transactions = useLoad(
    () => api.transactions(caseId, "?limit=100"),
    [caseId],
    "Transactions could not be loaded.",
  );
  const observations = useLoad(
    () => api.observations(caseId),
    [caseId],
    "Observations could not be loaded.",
  );
  const gateway = useLoad(
    () => api.gatewayRecords(caseId),
    [caseId],
    "Gateway records could not be loaded.",
  );
  const relationships = useLoad(() => api.relationships(caseId), [caseId]);
  const findings = useLoad(() => api.findings(caseId), [caseId]);
  const [kind, setKind] = useState("all");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Item | null>(null);

  const items = useMemo<Item[]>(() => {
    const rows: Item[] = [];
    for (const item of gateway.data?.items ?? []) {
      rows.push({
        kind: "gateway_record",
        id: item.object_id,
        label: `${String(item.record.source_record_id)} · ${String(item.record.merchant_domain)} · settlement ${String(item.record.payee_account_masked)}`,
        time: formatDateTime(item.time.value),
        classification: item.data_classification,
      });
    }
    for (const row of observations.data?.dns ?? []) {
      rows.push({
        kind: "dns_observation",
        id: row.id,
        label: `${row.domain} ${row.rrtype} ${row.rdata} · ${row.resolver}`,
        time: formatDateTime(row.observed_at),
        classification: row.data_classification,
      });
    }
    for (const row of observations.data?.hosting ?? []) {
      rows.push({
        kind: "hosting_observation",
        id: row.id,
        label: `${row.ip ?? "no address"} · ${row.provider_name ?? "no provider"}`,
        time: formatDateTime(row.observed_at),
        classification: row.data_classification,
      });
    }
    for (const row of transactions.data?.items ?? []) {
      rows.push({
        kind: "transaction",
        id: row.id,
        label: `${row.source_transaction_id ?? `line ${row.line_number}`} · ${row.account_masked} ${row.direction} ${formatAmount(row.amount, row.currency)} · ${row.reference_raw ?? "no reference"}`,
        time: formatBooking(row.booking_date, row.booking_time),
        classification: row.data_classification,
      });
    }
    return rows;
  }, [gateway.data, observations.data, transactions.data]);

  useEffect(() => {
    if (params.get("focus") !== "bridge" || selected || !relationships.data) return;
    const bridge = supportedGateway(relationships.data.items);
    const gatewayId = bridge?.support.find((item) => item.object_kind === "gateway_record")?.object_id;
    const record = items.find((item) => item.kind === "gateway_record" && item.id === gatewayId);
    if (record) setSelected(record);
  }, [items, params, relationships.data, selected]);

  const needle = search.trim().toLowerCase();
  const visible = items.filter(
    (item) =>
      (kind === "all" || item.kind === kind) &&
      (!needle || item.label.toLowerCase().includes(needle)),
  );
  const loading = transactions.loading || observations.loading || gateway.loading;
  const error = transactions.error ?? observations.error ?? gateway.error;
  const linked = selected
    ? (relationships.data?.items ?? []).filter((row) =>
        row.support.some((item) => item.object_id === selected.id),
      )
    : [];
  const cited = selected
    ? (findings.data?.items ?? []).filter((row) =>
        row.support_transaction_ids.includes(selected.id),
      )
    : [];

  return (
    <div className="split">
      <Panel
        title="Evidence repository"
        subtitle="Stored source records: statement rows, DNS observations, hosting notes, and gateway records. Analytical results are listed separately and are not evidence."
      >
        <div className="toolbar">
          <label className="field">
            Type
            <select value={kind} onChange={(event) => setKind(event.target.value)}>
              <option value="all">All source records</option>
              <option value="transaction">Statement rows</option>
              <option value="dns_observation">DNS observations</option>
              <option value="hosting_observation">Hosting notes</option>
              <option value="gateway_record">Gateway records</option>
            </select>
          </label>
          <label className="field">
            Search
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Reference, domain, ****0011"
            />
          </label>
          <span className="muted small">{visible.length} records shown</span>
        </div>
        {loading ? <Skeleton lines={6} /> : null}
        {error ? <ErrorBox message={error} /> : null}
        {!loading && visible.length === 0 ? <Empty>No stored record matches.</Empty> : null}
        {visible.length > 0 ? (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Record</th>
                  <th>Time</th>
                  <th>Class</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((item) => (
                  <tr
                    key={`${item.kind}-${item.id}`}
                    className={`clickable ${selected?.id === item.id ? "selected" : ""}`}
                    onClick={() => setSelected(item)}
                    tabIndex={0}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") setSelected(item);
                    }}
                  >
                    <td>{KIND_LABEL[item.kind] ?? item.kind}</td>
                    <td className="small">
                      {item.label}
                      <div className="muted mono">id {shortId(item.id)}</div>
                    </td>
                    <td className="small mono">{item.time}</td>
                    <td>
                      <span
                        className={`badge ${item.classification === "synthetic" ? "synthetic" : "neutral"}`}
                      >
                        {item.classification}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </Panel>
      <div className="sticky">
        {!selected ? (
          <Panel title="Evidence detail">
            <Empty>
              Select a record to see its source, provenance, and the analytical results that cite
              it.
            </Empty>
          </Panel>
        ) : (
          <Panel
            title={KIND_LABEL[selected.kind] ?? selected.kind}
            subtitle="As stored. Not edited by any analysis."
          >
            <RecordPanel caseId={caseId} kind={selected.kind} objectId={selected.id} />
            <hr className="divider" />
            <h3>Analytical results citing this record</h3>
            {linked.length === 0 && cited.length === 0 ? (
              <p className="muted small">None.</p>
            ) : null}
            <ul className="list-plain small">
              {linked.map((row) => (
                <li key={row.id}>
                  <Link to={`/cases/${caseId}/unified?rel=${row.id}`}>
                    {REL_LABEL[row.rel_type] ?? row.rel_type}
                  </Link>{" "}
                  <ClassBadge value={row.classification} />{" "}
                  <span className="mono">{row.method_version}</span>
                  <div className="muted">{row.limitation}</div>
                </li>
              ))}
              {cited.map((row) => (
                <li key={row.id}>
                  Finding: {row.finding_kind} · <span className="mono">{row.method_version}</span>
                  <div className="muted">{row.limitations}</div>
                </li>
              ))}
            </ul>
            <p className="muted small">
              VAGEXA does not certify records as forensically or legally admissible.
            </p>
          </Panel>
        )}
      </div>
    </div>
  );
}
