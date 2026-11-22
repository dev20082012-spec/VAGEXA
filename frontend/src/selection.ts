import type { GraphEdge, RelationshipRow } from "./api/types";

function preferSupported<T extends { classification: string | null }>(rows: T[]): T | undefined {
  return (
    rows.find((item) => item.classification === "CORROBORATED") ??
    rows.find((item) => item.classification === "DIRECTLY_SUPPORTED") ??
    rows[0]
  );
}

/** The gateway link two independent records agree on. A contradicted gateway record is not selected. */
export function supportedGateway(items: RelationshipRow[]): RelationshipRow | undefined {
  return preferSupported(items.filter((item) => item.rel_type === "gateway_merchant"));
}

export function supportedGatewayEdge(edges: GraphEdge[]): GraphEdge | undefined {
  return preferSupported(edges.filter((edge) => edge.kind === "gateway_merchant"));
}
