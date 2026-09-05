# ADR-013: OIDC Identity with Internal RBAC Authority

**Status:** Accepted

## Decision

Use provider-neutral OIDC authorization-code flow with PKCE for production
authentication. Map the stable external subject to a pre-provisioned active
user within one configured internal tenant. Never derive application roles or
tenant membership from unreviewed provider claims.

## Rationale and consequences

This creates a real standards boundary while preserving the tested tenant/RBAC
model. A valid organizational identity without an internal mapping is denied;
joiner/mover/leaver provisioning remains an external administrative process.
The callback consumes state before token exchange to prevent replay, so a
transient provider failure requires a fresh sign-in attempt.

