# Relationship classification

The stored assertion kinds remain `verified`, `inferred`, and `hypothesis`.
The review status is separate: `proposed`, `confirmed`, or `rejected`.

The API also returns a read-time `classification`: `DIRECTLY_SUPPORTED`,
`CORROBORATED`, `INFERRED`, `HYPOTHESIS`, `UNRESOLVED`, or `CONTRADICTED`.
It is computed from the stored rows and is not stored. Overlap is always
`UNRESOLVED`. The rules are in ADR 0017.

| Requested word | What is stored |
| --- | --- |
| Directly supported | `verified`. The claim is only as wide as the field: the narration contains the host, the observations contain the same key, or two rows cite the same reference. |
| Corroborated | Still `verified` or `inferred`. Two support ids are listed. The count is not a probability. |
| Inferred | `inferred`. Used for cross-case key counts, which are signals and not rows in the other case. |
| Hypothesis | Not auto-created by `correlate.v1`. Name similarity is not run. |
| Unresolved | Status `proposed`. The investigator has not decided. |
| Contradicted | Both observations remain. The engine does not delete the weaker one. |
| Accepted working link | Status `confirmed`. `assertion_kind` is unchanged. This is not a legal finding. |
| Rejected | Status `rejected`. The row stays. A later run does not insert it again. |

Confirm and reject are allowed for an assigned lead or investigator. An
analyst receives 403. A second decision on the same row is 409. The reason is
stored on `relationship_reviews` and is not written into the audit detail or
into the source narration.
