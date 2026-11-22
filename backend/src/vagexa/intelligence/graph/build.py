"""Build a case graph from rows already loaded. This function does not insert."""

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, time
from decimal import Decimal

import networkx as nx

from vagexa.intelligence.digital.normalise import OVERLAP_LIMITATION

FOUR = Decimal("0.0001")
PAYLOAD_LIMITATION = (
    "A connection is not common ownership, common control, or a criminal association. "
    "outside_horizon is not an attributed beneficiary. "
    "Components are weakly connected sets in this case, not communities."
)


@dataclass(frozen=True)
class GraphLeg:
    transaction_id: str
    account_id: str
    direction: str
    counterparty_account_id: str | None
    counterparty_resolution: str
    amount: Decimal
    currency: str
    booking_date: date
    booking_time: time | None
    provenance_id: str
    evidence_id: str | None
    reference: str | None
    rail: str
    method_version: str


@dataclass(frozen=True)
class GraphFlow:
    flow_id: str
    from_account_id: str
    to_account_id: str | None
    exit_kind: str | None
    amount: Decimal
    currency: str
    layer_to: int
    assertion_kind: str
    method_name: str
    method_version: str
    source_transaction_id: str
    trace_run_id: str
    booking_date: date | None


@dataclass(frozen=True)
class InfraObservation:
    kind: str
    observation_id: str
    provenance_id: str
    observed_at: str
    domain_id: str | None = None
    domain_name: str | None = None
    ip_id: str | None = None
    ip_label: str | None = None
    rrtype: str | None = None
    provider_name: str | None = None


@dataclass(frozen=True)
class GraphResidual:
    account_id: str
    amount: Decimal
    currency: str
    reason: str
    trace_run_id: str


@dataclass
class GraphEdge:
    id: str
    source: str
    target: str
    kind: str
    assertion_kind: str
    method_name: str
    method_version: str
    amount: str
    currency: str
    booking_date: str | None
    provenance_id: str | None
    evidence_ids: list[str]
    source_transaction_ids: list[str]
    layer_to: int | None = None
    trace_run_id: str | None = None
    explanation: str = ""
    support: list[dict[str, str]] = field(default_factory=list)


@dataclass
class GraphNode:
    id: str
    kind: str
    label: str
    data_classification: str
    residuals: list[dict[str, str]] = field(default_factory=list)


@dataclass
class GraphPayload:
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    components: list[dict[str, object]]
    truncated: bool
    path: list[str] | None
    path_reason: str | None
    limitations: str = PAYLOAD_LIMITATION


def _money(amount: Decimal) -> str:
    return f"{amount.quantize(FOUR):.4f}"


def _directed(leg: GraphLeg) -> tuple[str, str] | None:
    if leg.rail == "cash" or not leg.counterparty_account_id:
        return None
    if leg.counterparty_resolution not in {"structured_field", "narration_pattern"}:
        return None
    if leg.direction == "debit":
        return leg.account_id, leg.counterparty_account_id
    return leg.counterparty_account_id, leg.account_id


def _statement_edges(legs: list[GraphLeg]) -> list[GraphEdge]:
    grouped: dict[tuple[str, str, str, str, str], list[GraphLeg]] = defaultdict(list)
    edges: list[GraphEdge] = []
    seen_transactions: set[str] = set()
    for leg in legs:
        if leg.transaction_id in seen_transactions:
            continue
        seen_transactions.add(leg.transaction_id)
        ends = _directed(leg)
        if ends is None:
            if leg.rail == "cash" and leg.direction == "debit":
                edges.append(
                    GraphEdge(
                        id=f"tx:{leg.transaction_id}",
                        source=leg.account_id,
                        target=f"exit:{leg.transaction_id}",
                        kind="transfer",
                        assertion_kind="verified",
                        method_name="cash_exit",
                        method_version=leg.method_version,
                        amount=_money(leg.amount),
                        currency=leg.currency,
                        booking_date=leg.booking_date.isoformat(),
                        provenance_id=leg.provenance_id,
                        evidence_ids=[leg.evidence_id] if leg.evidence_id else [],
                        source_transaction_ids=[leg.transaction_id],
                        explanation="Cash left the account. No destination account is invented.",
                    )
                )
            continue
        key = (*ends, leg.currency, _money(leg.amount), leg.reference or leg.transaction_id)
        grouped[key].append(leg)
    for key, group in grouped.items():
        source, target = key[0], key[1]
        structured = [leg for leg in group if leg.counterparty_resolution == "structured_field"]
        chosen = structured or group
        assertion = "verified" if structured else "inferred"
        method = (
            "reference_join"
            if len(structured) > 1
            else ("structured_counterparty" if structured else "narration_extractor")
        )
        evidence = sorted({leg.evidence_id for leg in chosen if leg.evidence_id})
        transactions = sorted({leg.transaction_id for leg in chosen})
        earliest = min(
            chosen, key=lambda leg: (leg.booking_date, leg.booking_time is None, leg.transaction_id)
        )
        explanation = (
            "Both statement sides cite the same reference. This is not proof the same funds continued."
            if method == "reference_join"
            else (
                "One structured counterparty field states this transfer."
                if method == "structured_counterparty"
                else "Inferred from a narration pattern. It is not a verified fan-in or fan-out edge."
            )
        )
        edges.append(
            GraphEdge(
                id=f"tx:{transactions[0]}",
                source=source,
                target=target,
                kind="transfer",
                assertion_kind=assertion,
                method_name=method,
                method_version=earliest.method_version,
                amount=key[3],
                currency=key[2],
                booking_date=earliest.booking_date.isoformat(),
                provenance_id=earliest.provenance_id,
                evidence_ids=evidence,
                source_transaction_ids=transactions,
                explanation=explanation,
            )
        )
    return edges


def _attach_flows(edges: list[GraphEdge], flows: list[GraphFlow]) -> list[GraphEdge]:
    result = list(edges)
    for flow in flows:
        if flow.to_account_id is None or flow.exit_kind is not None:
            result.append(
                GraphEdge(
                    id=f"flow:{flow.flow_id}",
                    source=flow.from_account_id,
                    target=f"exit:{flow.flow_id}",
                    kind="transfer",
                    assertion_kind=flow.assertion_kind,
                    method_name=flow.method_name,
                    method_version=flow.method_version,
                    amount=_money(flow.amount),
                    currency=flow.currency,
                    booking_date=flow.booking_date.isoformat() if flow.booking_date else None,
                    provenance_id=None,
                    evidence_ids=[],
                    source_transaction_ids=[flow.source_transaction_id],
                    layer_to=flow.layer_to,
                    trace_run_id=flow.trace_run_id,
                    explanation="fifo.v1 cash or unresolved exit. No account is invented.",
                )
            )
            continue
        amount = _money(flow.amount)
        match = next(
            (
                edge
                for edge in result
                if edge.kind == "transfer"
                and edge.source == flow.from_account_id
                and edge.target == flow.to_account_id
                and edge.amount == amount
                and edge.currency == flow.currency
                and edge.assertion_kind == flow.assertion_kind
                and edge.trace_run_id is None
            ),
            None,
        )
        if match is not None:
            match.layer_to = flow.layer_to
            match.trace_run_id = flow.trace_run_id
            match.explanation = (
                f"Statement edge. fifo.v1 allocated this amount at layer {flow.layer_to}. "
                "This is not proof the same funds continued."
            )
            continue
        result.append(
            GraphEdge(
                id=f"flow:{flow.flow_id}",
                source=flow.from_account_id,
                target=flow.to_account_id,
                kind="transfer",
                assertion_kind=flow.assertion_kind,
                method_name=flow.method_name,
                method_version=flow.method_version,
                amount=amount,
                currency=flow.currency,
                booking_date=flow.booking_date.isoformat() if flow.booking_date else None,
                provenance_id=None,
                evidence_ids=[],
                source_transaction_ids=[flow.source_transaction_id],
                layer_to=flow.layer_to,
                trace_run_id=flow.trace_run_id,
                explanation=("fifo.v1 kept this edge because the amount or the assertion differs."),
            )
        )
    return result


def _component_id(node_ids: list[str]) -> str:
    digest = hashlib.sha256("|".join(node_ids).encode()).hexdigest()[:12]
    return f"c-{digest}"


def _support(edge: GraphEdge) -> list[dict[str, str]]:
    """The stored rows an edge was built from, so the client can open each one."""
    if edge.kind == "transfer":
        return [{"object_kind": "transaction", "object_id": item} for item in edge.source_transaction_ids]
    if edge.kind == "resolves_to":
        return [{"object_kind": "dns_observation", "object_id": item} for item in edge.evidence_ids]
    if edge.kind == "hosted_with":
        return [{"object_kind": "hosting_observation", "object_id": item} for item in edge.evidence_ids]
    if edge.kind == "infrastructure_overlap":
        kind = "hosting_observation" if edge.id.startswith("overlap-provider:") else "dns_observation"
        return [{"object_kind": kind, "object_id": item} for item in edge.evidence_ids]
    return []


def _node_kind(node_id: str) -> str:
    if node_id.startswith("exit:"):
        return "cash_exit"
    if node_id.startswith("domain:"):
        return "domain"
    if node_id.startswith("ip:"):
        return "ip"
    if node_id.startswith("provider:"):
        return "provider"
    return "account"


def _infrastructure_edges(observations: list[InfraObservation], labels: dict[str, str]) -> list[GraphEdge]:
    edges: list[GraphEdge] = []
    by_ip: dict[str, list[InfraObservation]] = defaultdict(list)
    by_provider: dict[str, list[InfraObservation]] = defaultdict(list)
    for item in observations:
        if item.kind == "dns" and item.domain_id and item.ip_id and item.domain_name and item.ip_label:
            labels[f"domain:{item.domain_id}"] = item.domain_name
            labels[f"ip:{item.ip_id}"] = item.ip_label
            by_ip[item.ip_id].append(item)
            edges.append(
                GraphEdge(
                    id=f"dns:{item.observation_id}",
                    source=f"domain:{item.domain_id}",
                    target=f"ip:{item.ip_id}",
                    kind="resolves_to",
                    assertion_kind="verified",
                    method_name="investigator_entry",
                    method_version="observe.v1",
                    amount="",
                    currency="",
                    booking_date=item.observed_at,
                    provenance_id=item.provenance_id,
                    evidence_ids=[item.observation_id],
                    source_transaction_ids=[],
                    explanation=(
                        f"Observed {item.rrtype} answer at {item.observed_at}. "
                        "A later answer does not remove this one."
                    ),
                )
            )
        if item.kind == "hosting" and item.provider_name and item.ip_id and item.ip_label:
            provider_key = item.provider_name.strip().lower()
            labels[f"ip:{item.ip_id}"] = item.ip_label
            labels[f"provider:{provider_key}"] = item.provider_name
            by_provider[provider_key].append(item)
            edges.append(
                GraphEdge(
                    id=f"host:{item.observation_id}",
                    source=f"ip:{item.ip_id}",
                    target=f"provider:{provider_key}",
                    kind="hosted_with",
                    assertion_kind="hypothesis",
                    method_name="investigator_entry",
                    method_version="observe.v1",
                    amount="",
                    currency="",
                    booking_date=item.observed_at,
                    provenance_id=item.provenance_id,
                    evidence_ids=[item.observation_id],
                    source_transaction_ids=[],
                    explanation=OVERLAP_LIMITATION,
                )
            )
    for ip_id, group in by_ip.items():
        domains = sorted({f"domain:{item.domain_id}" for item in group if item.domain_id})
        for left, right in zip(domains, domains[1:], strict=False):
            edges.append(
                GraphEdge(
                    id=f"overlap:{ip_id}:{left}:{right}",
                    source=left,
                    target=right,
                    kind="infrastructure_overlap",
                    assertion_kind="verified",
                    method_name="co_occurrence",
                    method_version="observe.v1",
                    amount="",
                    currency="",
                    booking_date=None,
                    provenance_id=None,
                    evidence_ids=[item.observation_id for item in group],
                    source_transaction_ids=[],
                    explanation=OVERLAP_LIMITATION,
                )
            )
    for provider_key, group in by_provider.items():
        addresses = sorted({f"ip:{item.ip_id}" for item in group if item.ip_id})
        for left, right in zip(addresses, addresses[1:], strict=False):
            edges.append(
                GraphEdge(
                    id=f"overlap-provider:{provider_key}:{left}:{right}",
                    source=left,
                    target=right,
                    kind="infrastructure_overlap",
                    assertion_kind="verified",
                    method_name="co_occurrence",
                    method_version="observe.v1",
                    amount="",
                    currency="",
                    booking_date=None,
                    provenance_id=None,
                    evidence_ids=[item.observation_id for item in group],
                    source_transaction_ids=[],
                    explanation=OVERLAP_LIMITATION,
                )
            )
    return edges


def build_graph(
    legs: list[GraphLeg],
    flows: list[GraphFlow],
    residuals: list[GraphResidual],
    *,
    labels: dict[str, str],
    data_classification: str,
    focus: str | None,
    max_hops: int,
    path_from: str | None = None,
    path_to: str | None = None,
    observations: list[InfraObservation] | None = None,
) -> GraphPayload:
    edges = _attach_flows(_statement_edges(legs), flows)
    edges.extend(_infrastructure_edges(observations or [], labels))
    graph: nx.MultiDiGraph = nx.MultiDiGraph()
    for edge in edges:
        graph.add_edge(edge.source, edge.target, key=edge.id, **{"edge_id": edge.id})
    residuals_by_account: dict[str, list[dict[str, str]]] = defaultdict(list)
    for residual in residuals:
        residuals_by_account[residual.account_id].append(
            {
                "amount": _money(residual.amount),
                "currency": residual.currency,
                "reason": residual.reason,
                "trace_run_id": residual.trace_run_id,
            }
        )
    account_ids = set(labels) | {edge.source for edge in edges} | {edge.target for edge in edges}
    account_ids |= set(residuals_by_account)
    kept = set(account_ids)
    truncated = False
    if focus is not None and focus in graph:
        distances = nx.single_source_shortest_path_length(graph.to_undirected(), focus, cutoff=max_hops)
        kept = set(distances)
        if residuals_by_account.get(focus) and focus not in kept:
            kept.add(focus)
        truncated = kept != account_ids and bool(account_ids - kept)
    elif focus is not None:
        kept = {focus}
        truncated = bool(account_ids - kept)
    edges = [edge for edge in edges if edge.source in kept and edge.target in kept]
    nodes: list[GraphNode] = []
    for node_id in sorted(kept | {edge.target for edge in edges} | {edge.source for edge in edges}):
        kind = _node_kind(node_id)
        if kind == "cash_exit":
            nodes.append(GraphNode(node_id, "cash_exit", "Cash exit", data_classification))
            continue
        nodes.append(
            GraphNode(
                node_id,
                kind,
                labels.get(node_id, "****" if kind == "account" else node_id),
                data_classification,
                residuals_by_account.get(node_id, []),
            )
        )
    component_graph = nx.MultiDiGraph()
    component_graph.add_nodes_from(node.id for node in nodes)
    component_graph.add_edges_from((edge.source, edge.target) for edge in edges)
    components: list[dict[str, object]] = [
        {"id": _component_id(sorted(component)), "node_ids": sorted(component)}
        for component in nx.weakly_connected_components(component_graph)
    ]
    components.sort(key=lambda item: str(item["id"]))
    path: list[str] | None = None
    path_reason: str | None = None
    if path_from and path_to:
        if path_from not in component_graph or path_to not in component_graph:
            path_reason = "outside_focus"
        else:
            try:
                found = nx.shortest_path(component_graph, path_from, path_to)
            except nx.NetworkXNoPath:
                path_reason = "no_path"
            else:
                if len(found) - 1 > max_hops:
                    path_reason = "beyond_hops"
                else:
                    path = list(found)
    for edge in edges:
        edge.support = _support(edge)
    return GraphPayload(
        nodes=sorted(nodes, key=lambda node: node.id),
        edges=sorted(edges, key=lambda edge: edge.id),
        components=components,
        truncated=truncated,
        path=path,
        path_reason=path_reason,
    )
