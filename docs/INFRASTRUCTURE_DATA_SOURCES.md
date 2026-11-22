# Infrastructure data sources

No external source is connected. The default is investigator entry and file
import of observations the investigator already holds.

| Source | What it would provide | Access in this deployment | Decision |
| --- | --- | --- | --- |
| Investigator entry | Name, address, time, note | Available to an assigned investigator | Stored |
| CSV or JSON import | The same fields, at most 500 rows and 1 MB | Available | Invalid rows are returned and not inserted |
| DNS resolver | A and AAAA for a name the investigator supplied | Flag `VAGEXA_PASSIVE_INTEL`, default false. No resolver configured | 409. Not called |
| RDAP | Registration fields actually returned | No contract, Phase 3 | Not collected |
| Certificate transparency | Names and certificate metadata for a supplied name | No adapter, Phase 3 | Not collected |
| IP and ASN registries | Network mapping for an address already in the case | No adapter, Phase 3 | Not collected |
| Passive DNS and threat feeds | Historical answers | Not licensed here | Not collected |

Rate limit for a live lookup is moot while the resolver is absent. Import is
capped at 500 observations so a paste cannot become a flood. The adapter does
not accept a URL and does not search the internet by suffix.

Privacy: another case that cites the same normalised name or address produces
a count only. Its answers, notes, and title are not returned. Logs record the
record type and the outcome, not the name, the address, or the note.

A failed lookup must not be stored as an empty answer. This release stores no
lookup result at all.
