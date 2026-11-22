# Session security

| Control | Implementation |
| --- | --- |
| Identifier | 32-byte URL-safe random value |
| Storage | SHA-256 hex in `sessions.token_hash` |
| Cookie | `vagexa_session`; `HttpOnly`; `SameSite=Lax`; `Path=/`; `Secure` when `VAGEXA_COOKIE_SECURE` is true |
| Lifetime | 12 hours from creation |
| Revocation | `revoked_at` on logout, password change, and account disable |
| Fixation | Login ignores any caller-chosen id and revokes the presented session |
| CSRF | Hash stored on the session. Plain token returned by login and `/me`, held in memory, required as `X-CSRF-Token` on unsafe methods |
| Headers | `nosniff`, `DENY` framing, `no-referrer`, `no-store` |

`VAGEXA_COOKIE_SECURE=false` is rejected unless the data mode is `synthetic`.

Deployment before official records still requires TLS, so `Secure` stays on,
plus the Phase 4 controls in the security implementation spec. This document
does not certify the deployment.
