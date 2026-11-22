# Hackathon access instructions

Open **https://vagexa-rj-demo.fly.dev**.

Sign in as the investigator account created for this deployment. The username
is `investigator`. The password is the same value already set locally as
`VAGEXA_BOOTSTRAP_PASSWORD`. It is not written in this repository. Put it in
the hackathon submission form, not in a commit.

The account's role is `investigator`. It is the lead on `SYN-DEMO`. It is not
an administrator, and it cannot open a case it is not assigned to. The
deployment accepts synthetic records only.

## What to show

1. The sign-in page states that the deployment holds synthetic demonstration data.
2. After sign-in, the dashboard shows `SYN-DEMO`.
3. Choose **Start the guided walkthrough**.
4. The walkthrough opens the overview, the opening payment, the three-hop trace, the fan-in and fan-out findings, the network, the infrastructure, the corroborated gateway link, the evidence record, and the report.

The records are fictional. A shared address or a contradicted gateway record
is not a finding of guilt.

## If sign-in fails

- Use `https://vagexa-rj-demo.fly.dev`, not a localhost address.
- Ten failed attempts for this username in fifteen minutes return 429. Wait and try again.
- `GET https://vagexa-rj-demo.fly.dev/health/ready` should return 200 and `"demonstration_case": "SYN-DEMO"` before a judge is asked to sign in.
- Do not turn off authentication.
