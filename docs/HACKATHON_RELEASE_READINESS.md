# Hackathon release readiness

Status: **READY WITH DOCUMENTED LIMITATIONS**.

The live investigation workflow passed on 2026-11-22. The application can be
shown to a judge. The official action-plan package is not finished, because
the public event site asks for a presentation and a wireframe as well as a
prototype, and those files were not produced here.

## What passed

A fresh browser signed in and completed `SYN-DEMO`:

1. Public URL.
2. Sign-in.
3. Investigation overview.
4. Transactions, including search and the outgoing filter.
5. Three-hop trace and the `outside_horizon` residual.
6. Fan-in and fan-out findings.
7. DNS and hosting observations, with the non-ownership limitation.
8. Corroborated, unresolved, and contradicted relationships.
9. Gateway record `SYN-PG-0001`.
10. Network graph and the selected gateway edge.
11. Report, including after refresh.

Details and the status of each requirement are in
[Final QA report](HACKATHON_FINAL_QA_REPORT.md).

## Release identity

| Item | Value |
| --- | --- |
| URL | https://vagexa-rj-demo.fly.dev |
| Commit | `677b4f2b65f86662ce601eb060692c3f1fc2a29b` |
| Subject | `15-live deploy` |
| Image | `registry.fly.io/vagexa-rj-demo:deployment-01M81ZDH9ZT3PFCW9FR3W2DBQF` |
| Machine | `78135d2c070608`, region `sin` |
| Dataset | `SYN-DEMO`, generator `demo.v2`, seed `20261122` |
| Mode | `synthetic` |
| Volume | `vagexa_data` (`vol_40oy9gwznegqomm4`) |

The QA documents and screenshots in this working tree are not part of commit
`677b4f2`. The running application is that commit. No application code was
changed after the judge session, so the site was not redeployed.

## Official submission requirements

Read from https://rajasthanpolicehackathon.in/ on 2026-11-22. This is not a
copy of a portal form.

| Public statement | How it applies |
| --- | --- |
| Problem statement | Financial Crime Infrastructure & Money-Trail Analysis System. |
| Register a team of up to 4 | The site lists the registration window as 1 Nov 2026 to 22 Nov 2026, 11:59 pm IST. The same page also showed an "extended" countdown. The portal fields and whether the team is already registered were not available here. |
| Action plan by 24 Nov 2026 | The site says PPT, wireframe, and HTML prototype. The live application covers the prototype. A PPT and a wireframe were not created. |
| Final | 28–29 Nov 2026, Rajasthan Police Academy, Jaipur, for the top 25 teams. |

A third-party Unstop listing describes a different screening form and
conflicting dates. It was not treated as the organiser's portal.

The repository remains proprietary, All Rights Reserved, with the copyright
owner still marked unconfirmed. The public homepage that was read does not
state an intellectual-property assignment. That term is unverified. Do not
add an ownership claim to the submission.

## Manual actions still required

1. Confirm the team is registered before the organiser's cutoff.
2. Submit the action plan in the portal: the problem statement, the live URL, and a PPT. A wireframe is also named on the public site.
3. Put the sign-in password in the portal or the presentation, not in git. The username is `investigator`.
4. Do not describe live DNS, certificates, or a copilot as working.
