# Phase 7 Production Security

## Controls implemented

- OIDC authorization-code + PKCE with state, nonce, browser binding, one-time
  transaction records, issuer/audience/signature/expiry validation, and no
  provider-controlled RBAC.
- HttpOnly, SameSite=Lax application sessions stored as hashes, with secure
  cookies outside local/test, expiration, revocation, disabled-account checks,
  and cross-site mutation rejection.
- Tenant-scoped repositories and server-side action authorization retained from
  earlier phases; pagination and OIDC subject lookup preserve tenant predicates.
- Trusted-host validation, explicit credentialed CORS allowlist, correlation-ID
  validation, HSTS in staging/production, CSP, frame denial, content sniffing
  prevention, referrer and permissions policies, and no-store API responses.
- Shared Redis rate limits in production for authentication, uploads, retrieval,
  questions, and model generation. Redis failure rejects protected work with a
  sanitized 503; local/test uses deterministic in-memory enforcement.
- Static AWS access keys are rejected in production. ECS execution and task
  roles separate image/secret retrieval from application S3/Bedrock permission.
  Terraform grants resource-scoped S3 and selected-model Bedrock calls.
- Containers run as non-root; API/worker/web use read-only roots, tmpfs scratch
  mounts, dropped capabilities, no-new-privileges, init processes, and bounded
  termination grace periods.

## Threats and residual risk

Replay of OIDC callbacks is blocked by transaction consumption before token
exchange; an upstream outage can therefore require the user to restart login.
This favors replay resistance. XSS remains principally controlled through Vue
escaping and CSP; no HTML model output is rendered. Application rate limiting
is not a substitute for ALB/WAF volumetric controls. Secrets referenced as ECS
environment variables require task restart after rotation and may be visible to
appropriately privileged process/debug tooling. Production activation requires
organization-specific IdP, WAF, alert routing, penetration testing, access
review, and secret-rotation exercises.

## Verification

Automated tests cover negative production configuration, header policy, hostile
Host values, correlation-ID sanitization, authentication throttling, cookie
cross-site rejection, OIDC happy path and replay rejection, disabled/expired
sessions, and existing cross-role/cross-tenant authorization cases. Dependency
audits and secret-pattern checks are CI gates. Image scanning is configured in
ECR and CI images are build-tested; a local CVE image scanner is run only when
the required scanner is installed.

