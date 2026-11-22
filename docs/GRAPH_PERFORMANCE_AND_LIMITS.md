# Graph performance and limits

The bound is the case plus the hop cap, not a cluster.

| Limit | Behaviour |
| --- | --- |
| `max_hops` above 5 | 422, before a graph is built |
| `max_hops` default | 3 |
| Focus | Undirected breadth-first cutoff. `truncated` is true when nodes are omitted |
| Date window | Edges outside the window are not loaded |
| Shortest path | One path. Longer than the cap is `beyond_hops`, not a second search |
| Case with no trace | Statement edges only. No invented FIFO layers |
| 2,000 disconnected transfers, focus hop 1 | The builder returned 1 edge in under 2 seconds in `test_two_thousand_edges_stay_bounded` |

There is no query timeout separate from the request, and there is no measured
plan from `EXPLAIN`. A few thousand edges fit the Phase 1 case size. A graph
database is not introduced. ADR 0004 names the measurements that would have to
be written down first.

The browser draws the payload it received. Searching and hiding an assertion
kind filters that payload. It does not add links. Layout positions are not
stored and are not evidence.

Cross-case work is an equality count on the account key. It does not walk
every case's transactions into one picture. A caller who cannot open the
other case still cannot open it because a key is shared.
