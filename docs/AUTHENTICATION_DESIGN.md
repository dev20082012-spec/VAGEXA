# Authentication design

VAGEXA uses one mechanism: a server-side session. The cookie holds an opaque
token. The database stores only its SHA-256 hash. There is no JWT and no
token in `localStorage`.

Public registration is not part of the product. An administrator creates
accounts. Password reset by email is not part of Phase 1. A signed-in user
can change their own password.

## Flow

1. `POST /api/v1/auth/login` checks Argon2id. Unknown users and bad passwords
   return the same 401 title. A disabled account returns 403.
2. A new session row is inserted. Any session presented on that request is
   revoked, so the server never adopts a caller-supplied session id.
3. The response sets `vagexa_session` (`HttpOnly`, `SameSite=Lax`, `Secure`
   unless synthetic loopback HTTP) and returns a CSRF token in the JSON body.
4. `GET /api/v1/auth/me` rotates that CSRF token and returns the new value.
   The browser keeps it in memory.
5. `POST`, `PATCH`, and `DELETE` must send `X-CSRF-Token`. The server compares
   the hash with the session row.
6. Logout sets `revoked_at`. Expired rows (`expires_at`, 12 hours) are rejected.
7. Password change rehashes with Argon2id, revokes every existing session, and
   issues a new one.
8. Disabling an account sets `status=disabled` and revokes its sessions. The
   user row stays so `created_by` and audit actor ids remain meaningful.
   There is no user delete.

Argon2id parameters are memory 19456 KiB, time cost 2, parallelism 1.
Ten failed logins for one username in 15 minutes return 429. The audit detail
stores the username, never the password.

## Assumptions

- The browser is same-site with the API through the Vite proxy or a single host.
- `SameSite=Lax` plus the CSRF header is the Phase 1 CSRF control.
- An external identity provider replaces local passwords in Phase 4. Case
  authorisation does not read the password table.
