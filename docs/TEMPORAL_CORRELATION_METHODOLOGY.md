# Temporal correlation methodology

Observation time, booking date, and collection time are different fields.
DNS rows store `observed_at`. Statement rows store `booking_date` and, when
the file had a clock, `booking_time`. Provenance stores `collected_at`. None
of these is rewritten to midnight.

`correlate.v1` does not generate a candidate from a time window. Two events
on the same day are linked only when an identifier rule also matches. Widening
a window therefore does not change the proposal set, and it does not change
the false-positive rate of this method. A later method that used windows would
have to publish the window on the run and would still not treat overlap as
proof.

Historical DNS answers stay. A later address does not delete the earlier
`resolves_to` edge and does not by itself create a financial link.

There is no certificate validity period in this release, because certificates
are not collected.
