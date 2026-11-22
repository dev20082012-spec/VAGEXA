# Analyst review workflow

1. An assigned investigator opens a case and loads statements and, where they
   hold them, DNS or hosting observations.
2. `POST /api/v1/cases/{case_id}/correlations` runs `correlate.v1` in the
   request. The response is the stored proposals, not a guess about progress.
3. The Correlation screen lists type, assertion, status, the explanation, the
   limitation, and the support ids.
4. A lead or investigator confirms or rejects. The reason is kept on a new
   review row. The relationship's assertion kind and its explanation stay as
   the method wrote them.
5. A rejected proposal remains visible and is not reinserted.
6. The network draws `mentioned_in` and `same_payment` while their status is
   not `rejected`. Overlap edges still come from the observations. A rejected
   containment edge drops off the next graph. The review row remains.

An analyst may run the correlation and may not decide it. Someone who is not
assigned receives 404. The audit records the action and the resulting status,
not the reason text and not account numbers.
