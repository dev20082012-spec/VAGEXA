# Unified correlation engine

`correlate.v1` proposes relationships from records the case already holds. It
does not create domains, transactions, or parties, and it does not call a
model.

A run reads current statement rows, DNS observations, and hosting notes. It
writes `relationships` with status `proposed`, support rows, and a finding
when an evidence record can be cited. A second run with the same keys inserts
nothing. Source observations and narrations are not updated.

The join between money and infrastructure is an identifier present in both:

1. a host or address extracted from a narration, and only if that same key is
   already an observation in the case;
2. the same IP on two DNS observations;
3. the same provider string on two hosting notes that also name addresses;
4. the same structured payment reference on two statement rows.

A shared day, with no shared key, creates nothing. Absence of a signal is not
stored as a relationship of type "unrelated".

Cross-case matches stay counts and masked or normalised keys. The other case's
title and rows are not returned.
