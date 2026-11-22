# Security test results

`python -m pytest` in `backend` is the run that covers this table. The
engineering report records the pass count from the latest execution.

| Area | Test | What it asserts |
| --- | --- | --- |
| Passwords | `test_password_is_hashed_not_stored_plaintext` | Argon2id, not equal to the password |
| Cookies | `test_cookie_is_httponly_and_login_does_not_echo_password` | `HttpOnly`, `SameSite=Lax`, password absent |
| Disabled account | `test_disabled_account_cannot_sign_in` | 403, sessions revoked by status change |
| Logout | `test_logout_revokes_the_session` | Later `/me` is 401 |
| Expiry | `test_expired_session_is_rejected` | Past `expires_at` is 401 |
| Fixation | `test_login_replaces_a_presented_session` | Old cookie dies after a new login |
| CSRF | `test_mutating_request_without_csrf_is_rejected` | 403, case not created |
| Password change | `test_password_change_revokes_other_sessions` | Other session 401, new password works |
| Lockout | `test_brute_force_lockout` | 10 failures then 429 |
| Privilege | `test_analyst_cannot_create_users_or_cases` | 403 |
| Cross-case | `test_cross_case_access_is_denied_without_the_title` | 404, title absent |
| Logs | `test_login_failure_audit_does_not_store_the_password` | Password not in stdout |
| Administrator | `test_unassigned_administrator_cannot_read_the_case` | 404 |

Password reset by email and public registration are not tested because they
are not implemented.
