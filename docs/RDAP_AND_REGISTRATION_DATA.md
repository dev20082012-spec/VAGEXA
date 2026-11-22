# RDAP and registration data

RDAP is not called. Registrar, registration date, expiration, nameservers, and
organisation fields are not stored. The observation list returns
`registration_reason: not_collected`.

A later adapter may insert only the fields a response actually contained, with
the retrieval time and the source. A redacted field stays redacted. A
registrant name does not create a party and does not merge an account. ADR 0011.

This deployment does not hold a registrar contract, and it does not scrape
WHOIS.
