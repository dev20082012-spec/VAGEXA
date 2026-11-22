import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, errorText } from "../api/client";
import type { ObservationList, RelationshipRow, SourceRecord } from "../api/types";
import { REL_LABEL, formatDateTime } from "../format";
import { ClassBadge, Empty, ErrorBox, Panel, Skeleton, useLoad } from "../ui";
import { RecordPanel } from "./RecordPanel";
import { supportedGateway } from "../selection";
import { useWorkspace } from "./context";

type Indicator = { kind: "domain" | "ip"; value: string };

export function InfrastructureTab() {
  const { caseId, reloadSummary } = useWorkspace();
  const [params] = useSearchParams();
  const observations = useLoad(
    () => api.observations(caseId),
    [caseId],
    "Observations could not be loaded.",
  );
  const relationships = useLoad(() => api.relationships(caseId), [caseId]);
  const gateway = useLoad(() => api.gatewayRecords(caseId), [caseId]);
  const [search, setSearch] = useState("");
  const [kind, setKind] = useState("all");
  const [selected, setSelected] = useState<Indicator | null>(null);
  const [open, setOpen] = useState<{ kind: string; id: string } | null>(null);

  const indicators = useMemo<Indicator[]>(() => {
    const body = observations.data;
    if (!body) return [];
    const domains = new Set(body.dns.map((row) => row.domain));
    for (const item of gateway.data?.items ?? []) {
      const name = item.record.merchant_domain;
      if (typeof name === "string") domains.add(name);
    }
    const addresses = new Set([
      ...body.dns.map((row) => row.rdata),
      ...body.hosting.map((row) => row.ip).filter((value): value is string => Boolean(value)),
    ]);
    return [
      ...Array.from(domains)
        .sort()
        .map((value) => ({ kind: "domain" as const, value })),
      ...Array.from(addresses)
        .sort()
        .map((value) => ({ kind: "ip" as const, value })),
    ];
  }, [observations.data, gateway.data]);

  useEffect(() => {
    if (params.get("focus") !== "bridge" || selected || !relationships.data) return;
    const bridge = supportedGateway(relationships.data.items);
    if (bridge?.to_label) setSelected({ kind: "domain", value: bridge.to_label });
  }, [params, relationships.data, selected]);

  const needle = search.trim().toLowerCase();
  const visible = indicators.filter(
    (item) =>
      (kind === "all" || item.kind === kind) &&
      (!needle || item.value.toLowerCase().includes(needle)),
  );

  return (
    <div className="stack">
      {observations.data ? <p className="notice caution">{observations.data.limitation}</p> : null}
      <div className="split">
        <Panel
          title="Indicator explorer"
          subtitle="Domains and addresses from stored observations and gateway records. Nothing here was looked up live."
        >
          <div className="toolbar">
            <label className="field">
              Search
              <input
                value={search}
                placeholder="syn-a.test or 203.0.113.50"
                onChange={(event) => setSearch(event.target.value)}
              />
            </label>
            <label className="field">
              Type
              <select value={kind} onChange={(event) => setKind(event.target.value)}>
                <option value="all">Domains and IP addresses</option>
                <option value="domain">Domains</option>
                <option value="ip">IP addresses</option>
              </select>
            </label>
          </div>
          {observations.loading ? <Skeleton lines={5} /> : null}
          {observations.error ? (
            <ErrorBox message={observations.error} onRetry={observations.reload} />
          ) : null}
          {observations.data && visible.length === 0 ? <Empty>No indicator matches.</Empty> : null}
          {visible.length > 0 ? (
            <table className="table">
              <thead>
                <tr>
                  <th>Indicator</th>
                  <th>Type</th>
                  <th>Observations</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((item) => {
                  const count =
                    item.kind === "domain"
                      ? observations.data?.dns.filter((row) => row.domain === item.value).length
                      : (observations.data?.dns.filter((row) => row.rdata === item.value).length ??
                          0) +
                        (observations.data?.hosting.filter((row) => row.ip === item.value).length ??
                          0);
                  const active = selected?.kind === item.kind && selected.value === item.value;
                  return (
                    <tr
                      key={`${item.kind}-${item.value}`}
                      className={`clickable ${active ? "selected" : ""}`}
                      onClick={() => {
                        setSelected(item);
                        setOpen(null);
                      }}
                      tabIndex={0}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") setSelected(item);
                      }}
                    >
                      <td className="mono">{item.value}</td>
                      <td>{item.kind === "domain" ? "Domain" : "IP address"}</td>
                      <td>{count}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : null}
          {observations.data ? (
            <p className="muted small" style={{ marginTop: 10 }}>
              Registration data: {observations.data.registration_reason.replace("_", " ")}.
              Certificates: {observations.data.certificate_reason.replace("_", " ")}. ASN and
              location: not collected.
            </p>
          ) : null}
        </Panel>
        <div className="sticky">
          {!selected || !observations.data ? (
            <Panel title="Indicator detail">
              <Empty>Select a domain or an address.</Empty>
            </Panel>
          ) : (
            <IndicatorDetail
              caseId={caseId}
              item={selected}
              observations={observations.data}
              relationships={relationships.data?.items ?? []}
              gateway={gateway.data?.items ?? []}
              onOpen={setOpen}
            />
          )}
          {open ? (
            <Panel title="Source record">
              <RecordPanel caseId={caseId} kind={open.kind} objectId={open.id} />
            </Panel>
          ) : null}
        </div>
      </div>
      <RecordObservation
        caseId={caseId}
        onStored={() => {
          observations.reload();
          reloadSummary();
        }}
      />
    </div>
  );
}

function IndicatorDetail({
  caseId,
  item,
  observations,
  relationships,
  gateway,
  onOpen,
}: {
  caseId: string;
  item: Indicator;
  observations: ObservationList;
  relationships: RelationshipRow[];
  gateway: SourceRecord[];
  onOpen: (value: { kind: string; id: string }) => void;
}) {
  const linked = relationships.filter(
    (row) => row.from_label === item.value || row.to_label === item.value,
  );
  if (item.kind === "domain") {
    const history = observations.dns
      .filter((row) => row.domain === item.value)
      .sort((left, right) => left.observed_at.localeCompare(right.observed_at));
    const records = gateway.filter((row) => row.record.merchant_domain === item.value);
    const answers = new Set(history.map((row) => row.rdata));
    return (
      <Panel title={item.value} subtitle="Domain">
        <h3>DNS observations, oldest first</h3>
        {history.length === 0 ? (
          <p className="muted small">
            No DNS observation is stored. That does not mean it does not resolve.
          </p>
        ) : null}
        <table className="table">
          <tbody>
            {history.map((row) => (
              <tr key={row.id}>
                <td className="mono small">{formatDateTime(row.observed_at)}</td>
                <td>{row.rrtype}</td>
                <td className="mono">{row.rdata}</td>
                <td>
                  <span
                    className={`badge ${row.data_classification === "synthetic" ? "synthetic" : "neutral"}`}
                  >
                    {row.resolver}
                  </span>
                </td>
                <td>
                  <button
                    className="link small"
                    type="button"
                    onClick={() => onOpen({ kind: "dns_observation", id: row.id })}
                  >
                    Source
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {answers.size > 1 ? (
          <p className="small muted">
            {answers.size} different addresses were recorded over time. Each answer is kept.
          </p>
        ) : null}
        <hr className="divider" />
        <h3>Gateway records naming this domain</h3>
        {records.length === 0 ? <p className="muted small">None.</p> : null}
        <ul className="list-plain small">
          {records.map((row) => (
            <li key={row.object_id}>
              <button
                className="link"
                type="button"
                onClick={() => onOpen({ kind: "gateway_record", id: row.object_id })}
              >
                {String(row.record.source_record_id)}
              </button>{" "}
              settlement account{" "}
              <span className="mono">{String(row.record.payee_account_masked)}</span>
            </li>
          ))}
        </ul>
        <Related caseId={caseId} rows={linked} />
        <p className="muted small">
          Registration, nameserver, and certificate data are not collected in this deployment.
        </p>
      </Panel>
    );
  }
  const domains = observations.dns.filter((row) => row.rdata === item.value);
  const hosting = observations.hosting.filter((row) => row.ip === item.value);
  return (
    <Panel title={item.value} subtitle="IP address. An address is not a location or an identity.">
      <h3>Domains observed at this address</h3>
      {domains.length === 0 ? <p className="muted small">None.</p> : null}
      <ul className="list-plain small">
        {domains.map((row) => (
          <li key={row.id}>
            <span className="mono">{row.domain}</span> at {formatDateTime(row.observed_at)}{" "}
            <button
              className="link"
              type="button"
              onClick={() => onOpen({ kind: "dns_observation", id: row.id })}
            >
              Source
            </button>
          </li>
        ))}
      </ul>
      <hr className="divider" />
      <h3>Hosting notes</h3>
      {hosting.length === 0 ? <p className="muted small">None.</p> : null}
      <ul className="list-plain small">
        {hosting.map((row) => (
          <li key={row.id}>
            {row.provider_name ?? "No provider string"} · {row.source_note}{" "}
            <button
              className="link"
              type="button"
              onClick={() => onOpen({ kind: "hosting_observation", id: row.id })}
            >
              Source
            </button>
          </li>
        ))}
      </ul>
      <Related caseId={caseId} rows={linked} />
      <p className="muted small">
        ASN, network owner, and geolocation are not collected in this deployment.
      </p>
    </Panel>
  );
}

function Related({ caseId, rows }: { caseId: string; rows: RelationshipRow[] }) {
  return (
    <>
      <hr className="divider" />
      <h3>Relationships</h3>
      {rows.length === 0 ? <p className="muted small">None proposed.</p> : null}
      <ul className="list-plain small">
        {rows.map((row) => (
          <li key={row.id}>
            <Link to={`/cases/${caseId}/unified?rel=${row.id}`}>
              {REL_LABEL[row.rel_type] ?? row.rel_type}
            </Link>{" "}
            <ClassBadge value={row.classification} />
            <div className="muted">
              {row.from_label} — {row.to_label}
            </div>
          </li>
        ))}
      </ul>
    </>
  );
}

function RecordObservation({ caseId, onStored }: { caseId: string; onStored: () => void }) {
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>, kind: "dns" | "hosting") {
    event.preventDefault();
    const target = event.currentTarget;
    const form = new FormData(target);
    setPending(true);
    setError(null);
    setMessage(null);
    try {
      const observedAt = new Date(String(form.get("observed_at"))).toISOString();
      const body: Record<string, string> =
        kind === "dns"
          ? {
              kind,
              domain: String(form.get("domain") || ""),
              rrtype: String(form.get("rrtype") || "A"),
              rdata: String(form.get("rdata") || ""),
              observed_at: observedAt,
            }
          : {
              kind,
              ip: String(form.get("ip") || ""),
              provider_name: String(form.get("provider_name") || ""),
              source_note: String(form.get("source_note") || ""),
              observed_at: observedAt,
            };
      await api.addObservation(caseId, body);
      target.reset();
      setMessage("Stored. Earlier observations were kept.");
      onStored();
    } catch (err) {
      setError(errorText(err, "The observation was not stored."));
    } finally {
      setPending(false);
    }
  }

  return (
    <details className="panel">
      <summary>
        <strong>Record an observation you already hold</strong>{" "}
        <span className="muted small">Investigator entry. The name is not resolved.</span>
      </summary>
      <div className="grid-2" style={{ marginTop: 12 }}>
        <form onSubmit={(event) => void submit(event, "dns")}>
          <h3>DNS answer</h3>
          <label className="field">
            Domain
            <input name="domain" required />
          </label>
          <label className="field">
            Type
            <select name="rrtype" defaultValue="A">
              <option value="A">A</option>
              <option value="AAAA">AAAA</option>
            </select>
          </label>
          <label className="field">
            Address
            <input name="rdata" required />
          </label>
          <label className="field">
            Observed at
            <input name="observed_at" type="datetime-local" required />
          </label>
          <button className="primary" type="submit" disabled={pending}>
            Store DNS observation
          </button>
        </form>
        <form onSubmit={(event) => void submit(event, "hosting")}>
          <h3>Hosting note</h3>
          <label className="field">
            IP address
            <input name="ip" />
          </label>
          <label className="field">
            Provider or nameserver string
            <input name="provider_name" />
          </label>
          <label className="field">
            Note
            <input name="source_note" required />
          </label>
          <label className="field">
            Observed at
            <input name="observed_at" type="datetime-local" required />
          </label>
          <button className="primary" type="submit" disabled={pending}>
            Store hosting note
          </button>
        </form>
      </div>
      {error ? <ErrorBox message={error} /> : null}
      {message ? <p className="notice">{message}</p> : null}
    </details>
  );
}
