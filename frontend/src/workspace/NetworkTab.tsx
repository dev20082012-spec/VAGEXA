import cytoscape from "cytoscape";
import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { GraphEdge, GraphNode, GraphPayload } from "../api/types";
import { KIND_LABEL, REL_LABEL, formatAmount, shortId } from "../format";
import { supportedGatewayEdge } from "../selection";
import { AssertionBadge, ClassBadge, Empty, ErrorBox, Panel, Skeleton, useLoad } from "../ui";
import { RecordPanel } from "./RecordPanel";
import { useWorkspace } from "./context";

const NODE_KINDS = ["account", "domain", "ip", "provider", "cash_exit"];

const STYLE: cytoscape.StylesheetJson = [
  {
    selector: "node",
    style: {
      label: "data(label)",
      "font-size": 10,
      color: "#142033",
      "text-valign": "bottom",
      "text-margin-y": 4,
      "text-background-color": "#fbfcfd",
      "text-background-opacity": 0.9,
      "text-background-padding": "1px",
      "border-width": 2,
      width: 30,
      height: 30,
    },
  },
  {
    selector: "node.n-account",
    style: { shape: "ellipse", "background-color": "#e6eef7", "border-color": "#1f3a5f" },
  },
  {
    selector: "node.n-domain",
    style: {
      shape: "diamond",
      "background-color": "#d8eef2",
      "border-color": "#0b6e82",
      width: 38,
      height: 38,
    },
  },
  {
    selector: "node.n-ip",
    style: {
      shape: "hexagon",
      "background-color": "#eef1f5",
      "border-color": "#5a6a7f",
      width: 34,
      height: 30,
    },
  },
  {
    selector: "node.n-provider",
    style: {
      shape: "round-rectangle",
      "background-color": "#f4f1fa",
      "border-color": "#5b4a9a",
      width: 44,
      height: 22,
    },
  },
  {
    selector: "node.n-cash_exit",
    style: { shape: "tag", "background-color": "#fcf1de", "border-color": "#925600" },
  },
  {
    selector: "node.holding",
    style: { "border-color": "#925600", "border-width": 4, "border-style": "double" },
  },
  {
    selector: "edge",
    style: {
      width: 1.5,
      "line-color": "#8696ab",
      "target-arrow-color": "#8696ab",
      "target-arrow-shape": "triangle",
      "arrow-scale": 0.8,
      "curve-style": "bezier",
      "font-size": 9,
      color: "#33445a",
      "text-background-color": "#fbfcfd",
      "text-background-opacity": 1,
      "text-rotation": "autorotate",
    },
  },
  {
    selector: "edge.fifo",
    style: {
      width: 3,
      "line-color": "#0b6e82",
      "target-arrow-color": "#0b6e82",
      label: "data(label)",
    },
  },
  {
    selector: "edge.k-resolves_to",
    style: { width: 1.2, "line-color": "#9fb0c4", "target-arrow-color": "#9fb0c4" },
  },
  {
    selector: "edge.k-hosted_with",
    style: { "line-style": "dotted", "line-color": "#8b7fb8", "target-arrow-color": "#8b7fb8" },
  },
  {
    selector: "edge.k-infrastructure_overlap",
    style: {
      "line-style": "dashed",
      width: 2,
      "line-color": "#c98a1a",
      "target-arrow-shape": "none",
      label: "overlap",
    },
  },
  {
    selector: "edge.k-gateway_merchant",
    style: {
      width: 3.5,
      "line-color": "#1d7348",
      "target-arrow-color": "#1d7348",
      label: "gateway record",
    },
  },
  {
    selector: "edge.k-mentioned_in",
    style: {
      "line-style": "dashed",
      width: 2,
      "line-color": "#1d7348",
      "target-arrow-color": "#1d7348",
      label: "named in narration",
    },
  },
  { selector: "edge.a-inferred", style: { "line-style": "dashed" } },
  { selector: "edge.a-hypothesis", style: { "line-style": "dotted" } },
  { selector: ".hidden", style: { display: "none" } },
  { selector: ".match", style: { "border-color": "#b42318", "border-width": 4 } },
  {
    selector: "edge.onpath",
    style: { "line-color": "#b42318", "target-arrow-color": "#b42318", width: 4 },
  },
  { selector: "node.onpath", style: { "border-color": "#b42318", "border-width": 4 } },
  {
    selector: ":selected",
    style: { "overlay-color": "#0b6e82", "overlay-opacity": 0.18, "overlay-padding": 6 },
  },
];

function edgeLabel(edge: GraphEdge): string {
  if (edge.layer_to) return `L${edge.layer_to} ${formatAmount(edge.amount, edge.currency)}`;
  return "";
}

export default function NetworkTab() {
  const { caseId } = useWorkspace();
  const [params] = useSearchParams();
  const canvas = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [hops, setHops] = useState("3");
  const [focus, setFocus] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [pathFrom, setPathFrom] = useState("");
  const [pathTo, setPathTo] = useState("");
  const [search, setSearch] = useState("");
  const [isolate, setIsolate] = useState(false);
  const [hiddenKinds, setHiddenKinds] = useState<Set<string>>(new Set());
  const [hiddenNodes, setHiddenNodes] = useState<Set<string>>(new Set());
  const [selection, setSelection] = useState<{ type: "node" | "edge"; id: string } | null>(null);
  const [openRecord, setOpenRecord] = useState<{ kind: string; id: string } | null>(null);

  const query = useMemo(() => {
    const qs = new URLSearchParams({ max_hops: hops });
    if (focus) qs.set("focus", focus);
    if (dateFrom) qs.set("booking_date_from", dateFrom);
    if (dateTo) qs.set("booking_date_to", dateTo);
    if (pathFrom && pathTo) {
      qs.set("path_from", pathFrom);
      qs.set("path_to", pathTo);
    }
    return `?${qs.toString()}`;
  }, [hops, focus, dateFrom, dateTo, pathFrom, pathTo]);

  const graph = useLoad<GraphPayload>(
    () => api.graph(caseId, query),
    [caseId, query],
    "The graph could not be loaded.",
  );
  const signals = useLoad(() => api.crossCaseSignals(caseId), [caseId]);
  const data = graph.data;

  const edgeKinds = useMemo(
    () => Array.from(new Set((data?.edges ?? []).map((edge) => edge.kind))).sort(),
    [data],
  );
  const nodesById = useMemo(
    () => new Map((data?.nodes ?? []).map((node) => [node.id, node])),
    [data],
  );

  useEffect(() => {
    if (!canvas.current || !data) return;
    const cy = cytoscape({
      container: canvas.current,
      elements: [
        ...data.nodes.map((node) => ({
          data: { id: node.id, label: node.label },
          classes: [`n-${node.kind}`, node.residuals.length ? "holding" : ""].join(" "),
        })),
        ...data.edges
          .filter((edge) => nodesById.has(edge.from) && nodesById.has(edge.to))
          .map((edge) => ({
            data: { id: edge.id, source: edge.from, target: edge.to, label: edgeLabel(edge) },
            classes: [
              `k-${edge.kind}`,
              edge.layer_to ? "fifo" : "",
              `a-${edge.assertion_kind}`,
              edge.classification ? `c-${edge.classification}` : "",
            ].join(" "),
          })),
      ],
      style: STYLE,
      layout: {
        name: "cose",
        animate: false,
        fit: true,
        padding: 30,
        nodeRepulsion: () => 9000,
        idealEdgeLength: () => 80,
      },
      wheelSensitivity: 0.2,
      minZoom: 0.2,
      maxZoom: 3,
    });
    cy.on("tap", "node", (event) => {
      setSelection({ type: "node", id: String(event.target.id()) });
      setOpenRecord(null);
    });
    cy.on("tap", "edge", (event) => {
      setSelection({ type: "edge", id: String(event.target.id()) });
      setOpenRecord(null);
    });
    cyRef.current = cy;
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [data, nodesById]);

  useEffect(() => {
    if (!data || params.get("select") !== "bridge" || selection) return;
    const bridge = supportedGatewayEdge(data.edges);
    if (bridge) setSelection({ type: "edge", id: bridge.id });
  }, [data, params, selection]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !data) return;
    const neighbours = new Set<string>();
    if (isolate && selection) {
      if (selection.type === "node") {
        neighbours.add(selection.id);
        for (const edge of data.edges) {
          if (edge.from === selection.id) neighbours.add(edge.to);
          if (edge.to === selection.id) neighbours.add(edge.from);
        }
      } else {
        const edge = data.edges.find((item) => item.id === selection.id);
        if (edge) {
          neighbours.add(edge.from);
          neighbours.add(edge.to);
        }
      }
    }
    const needle = search.trim().toLowerCase();
    const pathNodes = new Set(data.path ?? []);
    cy.batch(() => {
      cy.nodes().forEach((element) => {
        const node = nodesById.get(element.id());
        const hidden =
          (node && hiddenNodes.has(node.kind)) ||
          (isolate && selection !== null && !neighbours.has(element.id()));
        element.toggleClass("hidden", Boolean(hidden));
        element.toggleClass("match", Boolean(needle && node?.label.toLowerCase().includes(needle)));
        element.toggleClass("onpath", pathNodes.has(element.id()));
      });
      cy.edges().forEach((element) => {
        const edge = data.edges.find((item) => item.id === element.id());
        const hidden = !edge || hiddenKinds.has(edge.kind);
        element.toggleClass("hidden", hidden);
        const onPath = Boolean(
          edge &&
          edge.kind === "transfer" &&
          data.path?.some((id, index) => id === edge.from && data.path?.[index + 1] === edge.to),
        );
        element.toggleClass("onpath", onPath);
      });
      cy.elements().unselect();
      if (selection) cy.getElementById(selection.id).select();
    });
  }, [data, nodesById, hiddenKinds, hiddenNodes, search, isolate, selection]);

  function locate() {
    const cy = cyRef.current;
    const needle = search.trim().toLowerCase();
    if (!cy || !needle) return;
    const found = cy
      .nodes()
      .filter((element) => String(element.data("label")).toLowerCase().includes(needle));
    if (found.length) {
      cy.animate({ fit: { eles: found, padding: 80 } }, { duration: 250 });
      setSelection({ type: "node", id: found[0].id() });
    }
  }

  function toggle(set: Set<string>, value: string, update: (next: Set<string>) => void) {
    const next = new Set(set);
    if (next.has(value)) next.delete(value);
    else next.add(value);
    update(next);
  }

  const accounts = (data?.nodes ?? []).filter((node) => node.kind === "account");
  const selectedNode: GraphNode | null =
    selection?.type === "node" ? (nodesById.get(selection.id) ?? null) : null;
  const selectedEdge: GraphEdge | null =
    selection?.type === "edge"
      ? (data?.edges.find((edge) => edge.id === selection.id) ?? null)
      : null;
  const label = (id: string) => nodesById.get(id)?.label ?? shortId(id);

  return (
    <div className="stack">
      <Panel
        title="Network explorer"
        subtitle="Built from stored statement rows, the latest FIFO trace, DNS and hosting observations, and correlation proposals. A connection is not common ownership."
      >
        <div className="toolbar">
          <label className="field">
            Hops
            <select value={hops} onChange={(event) => setHops(event.target.value)}>
              {["1", "2", "3", "4", "5"].map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Centre on account
            <select value={focus} onChange={(event) => setFocus(event.target.value)}>
              <option value="">Whole case</option>
              {accounts.map((node) => (
                <option key={node.id} value={node.id}>
                  {node.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Booked from
            <input
              type="date"
              value={dateFrom}
              onChange={(event) => setDateFrom(event.target.value)}
            />
          </label>
          <label className="field">
            to
            <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
          </label>
          <label className="field">
            Path from
            <select value={pathFrom} onChange={(event) => setPathFrom(event.target.value)}>
              <option value="">—</option>
              {accounts.map((node) => (
                <option key={node.id} value={node.id}>
                  {node.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            to
            <select value={pathTo} onChange={(event) => setPathTo(event.target.value)}>
              <option value="">—</option>
              {accounts.map((node) => (
                <option key={node.id} value={node.id}>
                  {node.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Find entity
            <input
              value={search}
              placeholder="****0011 or syn-a.test"
              onChange={(event) => setSearch(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") locate();
              }}
            />
          </label>
          <button className="quiet" type="button" onClick={locate} disabled={!search.trim()}>
            Locate
          </button>
        </div>
        <div className="toolbar">
          <span className="muted small">Relationships:</span>
          {edgeKinds.map((kind) => (
            <label key={kind} className="check">
              <input
                type="checkbox"
                checked={!hiddenKinds.has(kind)}
                onChange={() => toggle(hiddenKinds, kind, setHiddenKinds)}
              />
              {REL_LABEL[kind] ?? kind}
            </label>
          ))}
          <span className="muted small">Entities:</span>
          {NODE_KINDS.filter((kind) => data?.nodes.some((node) => node.kind === kind)).map(
            (kind) => (
              <label key={kind} className="check">
                <input
                  type="checkbox"
                  checked={!hiddenNodes.has(kind)}
                  onChange={() => toggle(hiddenNodes, kind, setHiddenNodes)}
                />
                {KIND_LABEL[kind] ?? kind}
              </label>
            ),
          )}
        </div>
        <div className="legend" aria-label="Legend">
          <span>
            <i style={{ borderTopColor: "#8696ab" }} />
            Statement transfer (verified)
          </span>
          <span>
            <i style={{ borderTopColor: "#0b6e82", borderTopWidth: 4 }} />
            FIFO-allocated layer
          </span>
          <span>
            <i style={{ borderTopColor: "#1d7348", borderTopWidth: 4 }} />
            Supported cross-domain link
          </span>
          <span>
            <i style={{ borderTopColor: "#c98a1a", borderTopStyle: "dashed" }} />
            Technical overlap, unresolved
          </span>
          <span>
            <i style={{ borderTopColor: "#9fb0c4" }} />
            DNS observation
          </span>
          <span>
            <span className="dot" style={{ borderColor: "#1f3a5f" }} />
            Account
          </span>
          <span>
            <span
              className="dot"
              style={{ borderColor: "#0b6e82", borderRadius: 0, transform: "rotate(45deg)" }}
            />
            Domain
          </span>
          <span>
            <span className="dot" style={{ borderColor: "#5a6a7f", borderRadius: 2 }} />
            IP address
          </span>
          <span>
            <span className="dot" style={{ borderColor: "#925600" }} />
            Holds a residual
          </span>
        </div>
      </Panel>
      <div className="graph-layout">
        <div>
          {graph.error ? <ErrorBox message={graph.error} onRetry={graph.reload} /> : null}
          {graph.loading && !data ? <Skeleton lines={8} /> : null}
          {data && data.nodes.length === 0 ? (
            <Empty>No accounts or indicators are stored in this case.</Empty>
          ) : null}
          <div className="graph-canvas" ref={canvas} aria-label="Investigation graph" />
          {data ? (
            <div className="actions small" style={{ marginTop: 8 }}>
              <span className="muted">
                {data.nodes.length} entities, {data.edges.length} relationships,{" "}
                {data.components.length} connected groups
                {data.truncated ? ". The hop limit left some entities out." : "."}
                {data.path_reason ? ` No path: ${data.path_reason}.` : ""}
                {data.path ? ` Path of ${data.path.length - 1} hops highlighted.` : ""}
              </span>
              <button
                className="quiet"
                type="button"
                onClick={() => cyRef.current?.fit(undefined, 30)}
              >
                Reset view
              </button>
              <button
                className="quiet"
                type="button"
                onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 1.2)}
              >
                Zoom in
              </button>
              <button
                className="quiet"
                type="button"
                onClick={() => cyRef.current?.zoom(cyRef.current.zoom() / 1.2)}
              >
                Zoom out
              </button>
              <button
                className="quiet"
                type="button"
                onClick={() => setIsolate((value) => !value)}
                disabled={!selection}
              >
                {isolate ? "Show everything" : "Isolate selection"}
              </button>
              {focus ? (
                <button className="quiet" type="button" onClick={() => setFocus("")}>
                  Collapse to the whole case
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
        <div className="sticky">
          <Panel
            title={
              selectedNode
                ? selectedNode.label
                : selectedEdge
                  ? (REL_LABEL[selectedEdge.kind] ?? selectedEdge.kind)
                  : "Selection"
            }
          >
            {!selection ? <Empty>Select an entity or a relationship.</Empty> : null}
            {selectedNode && data ? (
              <NodeDetail
                node={selectedNode}
                graph={data}
                label={label}
                onExpand={() => setFocus(selectedNode.id)}
                onSelectEdge={(id) => setSelection({ type: "edge", id })}
              />
            ) : null}
            {selectedEdge ? (
              <>
                <dl className="kv">
                  <dt>From</dt>
                  <dd className="mono">{label(selectedEdge.from)}</dd>
                  <dt>To</dt>
                  <dd className="mono">{label(selectedEdge.to)}</dd>
                  {selectedEdge.amount ? (
                    <>
                      <dt>Amount</dt>
                      <dd className="mono">
                        {formatAmount(selectedEdge.amount, selectedEdge.currency)}
                      </dd>
                    </>
                  ) : null}
                  <dt>Time</dt>
                  <dd>{selectedEdge.booking_date ?? "See the source record"}</dd>
                  <dt>Assertion</dt>
                  <dd>
                    <AssertionBadge value={selectedEdge.assertion_kind} />{" "}
                    {selectedEdge.classification ? (
                      <ClassBadge value={selectedEdge.classification} />
                    ) : null}
                  </dd>
                  <dt>Method</dt>
                  <dd className="mono small">
                    {selectedEdge.method_name} {selectedEdge.method_version}
                  </dd>
                  {selectedEdge.layer_to ? (
                    <>
                      <dt>FIFO layer</dt>
                      <dd>{selectedEdge.layer_to}</dd>
                    </>
                  ) : null}
                  {selectedEdge.status ? (
                    <>
                      <dt>Review</dt>
                      <dd>{selectedEdge.status}</dd>
                    </>
                  ) : null}
                </dl>
                <p className="notice small" style={{ marginTop: 10 }}>
                  {selectedEdge.explanation}
                </p>
                <h3>Supporting records ({selectedEdge.support.length})</h3>
                <ul className="list-plain small">
                  {selectedEdge.support.map((item) => (
                    <li key={`${item.object_kind}-${item.object_id}`}>
                      <button
                        className="link"
                        type="button"
                        onClick={() =>
                          setOpenRecord({ kind: item.object_kind, id: item.object_id })
                        }
                      >
                        {KIND_LABEL[item.object_kind] ?? item.object_kind} {shortId(item.object_id)}
                      </button>
                    </li>
                  ))}
                </ul>
                {openRecord ? (
                  <div style={{ marginTop: 10 }}>
                    <RecordPanel caseId={caseId} kind={openRecord.kind} objectId={openRecord.id} />
                  </div>
                ) : null}
              </>
            ) : null}
          </Panel>
          <Panel
            title="Shared identifiers"
            subtitle="Other cases citing the same key. Their details are not shown."
          >
            {signals.data && signals.data.items.length === 0 ? (
              <p className="muted small">No exact key is shared with another case.</p>
            ) : null}
            <ul className="list-plain small">
              {(signals.data?.items ?? []).map((item) => (
                <li key={`${item.identifier_kind}-${item.masked}`}>
                  <span className="mono">{item.masked}</span> appears in {item.other_case_count}{" "}
                  other case
                  {item.other_case_count === 1 ? "" : "s"}.
                  <div className="muted">{item.limitations}</div>
                </li>
              ))}
            </ul>
          </Panel>
        </div>
      </div>
    </div>
  );
}

function NodeDetail({
  node,
  graph,
  label,
  onExpand,
  onSelectEdge,
}: {
  node: GraphNode;
  graph: GraphPayload;
  label: (id: string) => string;
  onExpand: () => void;
  onSelectEdge: (id: string) => void;
}) {
  const touching = graph.edges.filter((edge) => edge.from === node.id || edge.to === node.id);
  const transfers = touching.filter((edge) => edge.kind === "transfer");
  const other = touching.filter((edge) => edge.kind !== "transfer");
  return (
    <>
      <dl className="kv">
        <dt>Type</dt>
        <dd>{KIND_LABEL[node.kind] ?? node.kind}</dd>
        <dt>Identifier</dt>
        <dd className="mono small">{node.id}</dd>
        <dt>Classification</dt>
        <dd>{node.data_classification}</dd>
        <dt>Transfers</dt>
        <dd>
          {transfers.filter((edge) => edge.from === node.id).length} out,{" "}
          {transfers.filter((edge) => edge.to === node.id).length} in
        </dd>
      </dl>
      {node.residuals.map((item) => (
        <p
          key={`${item.reason}-${item.amount}`}
          className="notice caution small"
          style={{ marginTop: 10 }}
        >
          Residual {formatAmount(item.amount, item.currency)}: {item.reason}. Not an attributed
          beneficiary.
        </p>
      ))}
      {node.kind === "account" ? (
        <p style={{ marginTop: 10 }}>
          <button className="quiet" type="button" onClick={onExpand}>
            Expand the neighbourhood
          </button>
        </p>
      ) : null}
      <h3>Connected</h3>
      <ul className="list-plain small">
        {touching.slice(0, 14).map((edge) => {
          const peer = edge.from === node.id ? edge.to : edge.from;
          return (
            <li key={edge.id}>
              <button className="link" type="button" onClick={() => onSelectEdge(edge.id)}>
                {REL_LABEL[edge.kind] ?? edge.kind}
              </button>{" "}
              {edge.from === node.id ? "to" : "from"} <span className="mono">{label(peer)}</span>
              {edge.amount ? ` · ${formatAmount(edge.amount, edge.currency)}` : ""}
            </li>
          );
        })}
      </ul>
      {touching.length > 14 ? (
        <p className="muted small">{touching.length - 14} more not listed.</p>
      ) : null}
      {other.length === 0 && transfers.length === 0 ? (
        <p className="muted small">No relationship in this view.</p>
      ) : null}
    </>
  );
}
