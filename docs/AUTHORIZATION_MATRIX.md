# Authorization matrix

Role names are the approved set: `administrator`, `investigator`, `analyst`,
`auditor`. A separate supervisor role is not implemented. Global permissions
live in `role_permissions`. Case permissions come from `case_assignments.case_role`.
The API checks both. Hidden buttons are not a control.

## Global permissions

| Permission | administrator | investigator | analyst | auditor |
| --- | --- | --- | --- | --- |
| `users.manage` | yes | no | no | no |
| `cases.create` | yes | yes | no | no |
| `cases.assign` | yes | no | no | no |

`cases.assign` does not grant the ability to read the case.

## Case role permissions

| Permission | lead | investigator | analyst | auditor |
| --- | --- | --- | --- | --- |
| `cases.read` | yes | yes | yes | yes |
| `cases.mutate` | yes | yes | no | no |
| `analysis.run` | yes | yes | yes | no |
| `audit.read` | yes | yes | yes | yes |

The creator of a case is assigned `lead` in the same transaction. Anyone else,
including a global administrator, receives 404 until assigned. The response
does not include the case title.

Future organisation boundaries can be a column on `users` and `cases`. They
are not required for Phase 1, and assignments already sit between those tables.

## Enforcement

| Action | Rule |
| --- | --- |
| Create a user, disable a user | `users.manage` |
| Create a case | `cases.create`, then classification check |
| List or open a case | Assignment and `cases.read` |
| Run a trace, indicator rule, or statement walk | Assignment and `analysis.run`. An auditor can read the result and cannot start a run. |
| Assign a user to a case | `cases.assign` |
| Change own password, logout | Authenticated session and CSRF |
| Sign in | Active account, Argon2id, lockout |
