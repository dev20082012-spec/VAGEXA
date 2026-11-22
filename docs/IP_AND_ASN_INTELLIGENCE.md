# IP and ASN intelligence

Addresses are parsed with the standard library and stored as PostgreSQL
`inet`. `192.168.001.002` becomes `192.168.1.2`. IPv6 is stored in compressed
form, so `2001:0db8:0000::1` is `2001:db8::1`. A value that is not an address
is rejected. An A record must be IPv4 and an AAAA record must be IPv6.

There is no ASN table and no geolocation. An address is not a physical
location. Registry ownership is not collected.

On the graph, an address is an `ip` node labelled with the canonical address,
visible only inside a case the caller can read. History is the set of
`resolves_to` edges and their times.

A lookup target that is private, loopback, link-local, multicast, reserved, or
unspecified is refused before any connection. So are `localhost`, a URL, and
names ending in `.local` or `.internal`. That guard is `refuse_lookup_target`.
It does not call `socket` or `getaddrinfo`.
