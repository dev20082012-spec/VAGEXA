# Entity resolution methodology

Resolution follows the graph data model. It does not turn a resemblance into
an identity.

| Situation | Result | Assertion |
| --- | --- | --- |
| Same normalised account number and IFSC, or the same VPA | One account row, reused | The instrument key. Not a claim about the holder. |
| Both statement sides share a reference, amount, currency, and the two accounts | One transfer edge citing both transaction ids | `verified`, method `reference_join` |
| One structured counterparty field | One transfer edge | `verified`, method `structured_counterparty` |
| Narration pattern only | One transfer edge | `inferred`, method `narration_extractor`. Not a verified fan-in or fan-out count. |
| Same amount and date, different reference | Separate edges | Not joined. |
| Similar account numbers or similar holder names | Separate nodes | No merge. No candidate row is promoted by a threshold. |
| Exact key also cited in another case | A signal: masked key and `other_case_count` | `inferred`, method `exact_identifier`. Not a shared holder. |

There is no probabilistic matcher and no score that becomes `verified`.
Unmatched counterparties produce no edge. A human merge, when that workflow
exists, is a later `same_as` decision. This release does not infer one.

Contradictory pictures are kept. A FIFO allocation whose amount differs from
the statement is a second edge, not an average.
