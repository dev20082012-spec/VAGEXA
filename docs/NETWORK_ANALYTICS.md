# Network analytics

These are the algorithms the graph request runs. Each one is deterministic.
None of them is a finding of guilt.

## Multi-hop neighbourhood

Input: the case edges and an optional focus account. Parameter: `max_hops`,
1 to 5, default 3. Output: nodes within that undirected distance, with
directed edges between them, and `truncated` when nodes were dropped.
Complexity is a breadth-first search of the case subgraph. A missing focus
account is 404. The client cannot submit a traversal expression.

Interpretation: these are the statement and FIFO links inside the cap. The
account at the edge of the cap is not the end of the money.

## Directed shortest path

Input: `path_from`, `path_to`, and the same hop cap. Output: one directed
path, or `path_reason` of `no_path`, `beyond_hops`, or `outside_focus`.
NetworkX shortest path on the loaded multigraph. The search is bounded by the
case and then rejected when the path is longer than the cap.

Interpretation: a path is a sequence of stored transfers. It is not proof that
one sum of money travelled the whole way. FIFO layers, when present, are the
allocation. A statement edge without `layer_to` was not allocated by the
selected trace.

## Weakly connected components

Input: the nodes and edges after the hop filter. Output: `components`, each
with a stable id from the sorted node ids and the node list. NetworkX
`weakly_connected_components`. Direction is ignored for membership and kept on
the edges.

Interpretation: a component is a set that touches inside this response. It is
not a community, a gang, or a network of offenders. Shared membership does not
establish a common holder.

## Not computed

| Algorithm | Why it is absent |
| --- | --- |
| Degree centrality | A count of edges can be read from the component. A rank is not stored. |
| Betweenness | It would mark an account as a bridge without an investigative question. |
| Community detection | The component field would be mistaken for a criminal group. ADR 0016. |
| Cycle code | A return can be seen by walking the edges. No `CYCLE` indicator is written. ADR 0015. |

Tests cover the horizon-3 chain, a one-hop focus cut, a path inside and beyond
the cap, duplicate edges, similar account numbers left unmerged, a narration
edge kept `inferred`, a cash exit that is not an account, a 2,000-edge build
that returns one edge at hop 1, hop 6 rejected, a date window, and a
cross-case count that omits the other title.
