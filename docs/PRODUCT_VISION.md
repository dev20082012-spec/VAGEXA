# Product vision

VAGEXA is an investigation workspace for authorised officers and analysts who
must see how money moved, which accounts sat on that path, and which domains,
DNS records, IP addresses, and hosting observations appear in the same matter.

The first external milestone is the Rajasthan Police Hackathon 2026, organised
by R4C (Rajasthan Cyber Crime Control Centre). The public problem statement
that matches this product is **Financial Crime Infrastructure & Money-Trail
Analysis System**: analyse bank statements, trace suspected mule-account
transactions, examine domains and hosting, and show links between cases. The
public brief is cited, not copied, from
[rajasthanpolicehackathon.in](https://rajasthanpolicehackathon.in/). Event dates
on public pages have differed; confirm them on that site before relying on them.

The long-term product is the same system, hardened for repeated casework. The
hackathon is a slice, not a separate prototype that will be thrown away.

## The problem

A financial-cyber complaint arrives as fragments. One file is a victim
statement. Another is a mule account that cashed out within hours. A third
complaint names the same VPA. A domain in the narration resolves to an address
already seen on a different case. None of those facts becomes an investigative
picture until someone joins them, and the join has to remain inspectable later.

Investigators need to:

- read heterogeneous bank statements as one transaction model;
- follow value across a small number of hops, including splits and merges;
- see fan-in and fan-out without treating the pattern as proof;
- attach passive infrastructure observations to the same case;
- notice that two cases share an account, a VPA, or a domain;
- export a report that shows the method, the sources, and the gaps.

## Users

| User | Need |
| --- | --- |
| Investigator | Build a case, confirm or reject a suggested link, export a report. |
| Analyst | Run traces and indicators. Cannot confirm a relationship as verified beyond its source. |
| Auditor | Read what was done, by whom, and from which record. Cannot change the case. |
| Administrator | Manage accounts and assignments. Does not gain unspoken access to case narratives beyond the audit need. |

Victims and the public are not users of this application.

## What the product produces

- A case file of source records, normalised transactions, and observations.
- Trace runs that assign layer 1, layer 2, and layer 3 inside a named policy.
- Indicators with the transactions that fired them.
- A case graph whose edges say whether they are verified, inferred, or hypotheses.
- Cross-case signals that respect access to the other case.
- Copilot answers whose sentences cite evidence the tools actually returned.
- An export that a reviewer can compare with the source rows.

## What the product refuses to produce

- A declaration that a person is a mule, an offender, or the owner of an account.
- A risk score presented as proof.
- A path continued past the supplied records by guessing the next account.
- A mixture of synthetic demonstration data and official records in one case.
- An AI finding that has no source row behind it.

## Glossary

| Term | Meaning in VAGEXA |
| --- | --- |
| Case | The investigator's unit of work. It holds complaints, files, and findings. |
| Complaint | A reported fraud that may name amounts, accounts, or domains. |
| Account | A bank account (number and IFSC) or a UPI VPA. Names are not accounts. |
| Transaction | One debit or credit row from a statement, tied to the source line. |
| Trace run | One execution of a versioned allocation policy from confirmed seeds. |
| Layer | The hop distance of value in that trace run. It is not a permanent label on an account. |
| Indicator | A versioned rule match with supporting transaction ids. |
| Assertion kind | `verified`, `inferred`, or `hypothesis`. Defined in [Evidence and provenance](EVIDENCE_AND_PROVENANCE.md). |
| Provenance | The source, collector, time, and method for a record. |
| Data classification | `official`, `public_intelligence`, `synthetic`, `derived`, or `unverified`. |

`verified` is used because investigators must separate source facts from
inference. In this product it means "a cited source field states this". It does
not mean "judicially proved".

## Design stance

Correctness, explainability, and maintainability outrank feature count. The
engines in the vision — financial, graph, digital infrastructure, correlation,
copilot, and evidence — share one case and one provenance model. They are not
six applications.

Business rules stay out of controllers and out of the screen. Each rule is a
module with a version and a test. Authentication, authorisation, and audit are
part of the first runnable slice, not a later coat of paint.

## Non-goals

- Core banking, payment initiation, or account freezing.
- Scraping the National Cybercrime Reporting Portal or any bank.
- Covert surveillance, intrusion, or malware analysis.
- Face recognition, CDR, or social-media monitoring. Those are other problem
  statements at the same hackathon, not this product.
- A general chatbot over the public internet.

## Success

An investigator can load a labelled synthetic scenario, recover the planted
multi-hop paths, see a shared beneficiary across two complaints, see the
attached domain observation, and export a report that distinguishes source rows
from FIFO allocation. A reviewer can point at every edge and land on a source
record or a named method. The same path, run again on the same inputs, produces
the same flows.
