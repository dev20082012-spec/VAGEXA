# Final demonstration script

About five minutes. Verified against https://vagexa-rj-demo.fly.dev on
2026-11-22. Sign in as `investigator`. The password is the one supplied with
the submission, not a value in this file.

If a page is slow, wait for the synthetic banner. Do not upload a file.

## 00:00–00:30 — Introduce VAGEXA

Stay on the sign-in page.

Say: investigators receive statements, account references, and domain names
as separate fragments. VAGEXA keeps those records, traces the money the
statements support, and shows which infrastructure links the records actually
justify. This deployment is synthetic. It is not an official case.

## 00:30–01:15 — Open the investigation

Sign in. On the dashboard, choose **Start the guided walkthrough**.

Expected: `SYN-DEMO`, status open, classification synthetic, 25 transactions,
and a residual of ₹1,00,000.00 on `****0013` marked `outside_horizon`.

Say: every figure is a count of stored rows. The objective is to see which
records connect a fictional merchant payment to later transfers, and which
links remain unresolved.

Recovery: choose **Open the investigation** instead of the walkthrough.

## 01:15–02:00 — Financial intelligence

Choose **Next** twice, or open **Financial intelligence**, then **Fund flow**.

Expected: `fifo.v1` allocates `****0001` → `****0011` → `****0012` →
`****0013`. The residual stays on `****0013`.

Then choose **Next** once more, or open **Findings**.

Expected: fan-in and fan-out on the account ending `0030`. The text says
these are rule matches, not findings of guilt.

Say: the trace stops at the horizon. The next statement debit is not called
the beneficiary. The pattern is a rule match on 16 and 17 January.

Recovery: the overview states the same residual and the same two rules.

## 02:00–02:45 — Digital infrastructure

Choose **Next**, or open **Infrastructure** and select `syn-a.test`.

Expected: A `203.0.113.50` on 14 January and a later answer
`203.0.113.60`. `syn-b.test` uses the first address. The limitation says a
shared address does not establish a common operator. The resolver is
`synthetic_fixture`.

Say: both DNS answers are kept. Co-occurrence is not ownership.

Recovery: the report's infrastructure section lists the same observations.

## 02:45–03:30 — Unified correlation

Choose **Next**, or open **Unified intelligence**.

Expected: the selected row is `****0011` to `syn-a.test`, corroborated,
proposed, method `correlate.v2`. The narration row from `****0001` agrees.
`syn-a.test` with `syn-b.test` is unresolved. `****0071` to `syn-d.test` and
`syn-e.test` are contradicted.

Say: a gateway record and the narration name the same host. Two later
gateway records name different hosts for one payment, and both are kept.
Agreement is not identity. Disagreement is not deleted.

Recovery: search `SYN-PG-0001` on the Evidence tab.

## 03:30–04:15 — Investigation graph

Choose **Next**, or open **Network explorer**.

Expected: the canvas shows the statement chain and the domains. The side
panel is the gateway edge from `****0011` to `syn-a.test`, corroborated.

Say: the graph is the same rows as the lists. The selected edge cites the
gateway record and the statement rows.

Recovery: stay on Unified intelligence. The same edge is listed there.

## 04:15–05:00 — Evidence and the report

Choose **Next** to Evidence. The selected record is `SYN-PG-0001`,
₹1,00,000.00, merchant `syn-a.test`, source `synthetic_payment_gateway`,
marked synthetic.

Choose **Next** again, or open **Report**.

Expected: 14 statements, 25 transactions, 6 DNS observations, 2 hosting
notes, 3 gateway records. The opening text says no section is a finding of
guilt, ownership, or identity. Print is available.

Say: the report is assembled from the stored case. It lists what was
observed, what a named method derived, and what is still unresolved.

Recovery: read the overview. It uses the same summary.
