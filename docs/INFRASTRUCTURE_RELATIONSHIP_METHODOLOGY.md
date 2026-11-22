# Infrastructure relationship methodology

Relationships are derived when the case graph is built. They are not a second
copy that can drift from the observations, except that the observations
themselves are the stored evidence.

| Edge | When | Assertion | Meaning |
| --- | --- | --- | --- |
| `resolves_to` | One DNS observation | `verified` | That answer was recorded at that time. |
| `hosted_with` | A hosting note names a provider string and an address | `hypothesis` | The note says so. |
| `infrastructure_overlap` | Two domains in the case have answers for the same address, or two addresses carry the same provider string | `verified` for co-occurrence only | The observations contain the same key. |

Every overlap edge uses this limitation, unchanged:

`Shared hosting, a shared address, or shared DNS does not establish common ownership, common control, or a common operator.`

The system does not create a party, an owner, or a criminal association.
Similar names are not merged. A domain and a subdomain stay distinct. Two
addresses for one name stay as two `resolves_to` edges.

Financial transfer edges are built by the same function and are not rewritten
by an observation.
