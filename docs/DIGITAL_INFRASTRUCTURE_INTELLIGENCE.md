# Digital infrastructure intelligence

Investigators record domains and addresses they already hold. The engine keeps
those observations, normalises the keys, and shows technical overlap. It does
not decide who operates the infrastructure.

Live DNS, RDAP, certificate transparency, and ASN registries are not called.
`VAGEXA_PASSIVE_INTEL` defaults to false. The lookup route returns 409. When
the flag is on, a private, loopback, or link-local target is refused, and a
public name still returns 409 because no resolver is configured. No socket is
opened.

## Modules

| Piece | Role |
| --- | --- |
| `intelligence/digital/normalise.py` | Domain and IP keys, lookup refusal |
| `application/infrastructure_service.py` | Store and list observations, import files |
| `intelligence/graph/build.py` | `resolves_to`, `hosted_with`, and overlap edges |
| `api/routers/infrastructure.py` | HTTP only |

Financial transfers are unchanged. An observation does not create an account
edge.

## What is stored

- One `domain_names` row per normalised name.
- One `ip_addresses` row per canonical address.
- Append-only `dns_observations` for A and AAAA, tied to the case.
- Append-only `hosting_observations` for an address and/or a provider string
  the investigator typed, with their note.

A second answer for the same name is a new row. The first row stays.
Registration and certificates are empty lists with reason `not_collected`.
