# Phase 6 Authentication and Provider Boundary

## Local authentication

The normal application uses email and password. Argon2id hashes are stored on the user record; plaintext passwords are never stored, returned, logged, or added to telemetry. Successful authentication creates a random opaque session token. Only its SHA-256 digest is stored in `user_sessions`; the raw token is delivered in a `HttpOnly`, `SameSite=Lax` cookie. Local HTTP disables `Secure`; nonlocal environments set it.

Sessions expire after eight hours by default, or thirty days when the user explicitly selects the remembered-device option. Logout revokes the database record and removes the cookie. Expired, revoked, disabled-user, and unknown sessions fail closed. Cookie-authenticated cross-site mutations are rejected using Origin and Fetch Metadata checks. CORS permits credentials only from configured origins.

The legacy `/auth/dev/*` endpoints remain local/test-only for deterministic regression scripts. They are absent from the normal UI and cannot be enabled when `APP_ENV` is staging or production. They are not a production sign-in mechanism.

Development accounts use the shared password `HarborView!Local2026`:

- `avery.morgan@example.invalid` — claims adjuster
- `jordan.lee@example.invalid` — supervisor
- `riley.chen@example.invalid` — compliance reviewer
- `casey.patel@example.invalid` — administrator

All are fictional and local-only.

## Enterprise identity extension

`IdentityProvider` remains the verification port. A production adapter can validate OIDC access or identity tokens from Microsoft Entra ID, Okta, Auth0, Cognito, or another approved IdP, map the stable subject and tenant to an application user, and then rely on existing application RBAC. No OIDC provider is configured or claimed in the local environment.

The frontend never selects or assigns roles. Navigation visibility is a usability reflection of server permissions; every API action remains server-authorized.

## Bedrock adapter

`BedrockConverseProvider` implements the Phase 5 `ModelProvider` port using the Bedrock Runtime Converse API. It requests JSON-schema-constrained output, does not expose tools, labels all evidence as untrusted data, sends only opaque citation handles, reports provider token usage when supplied, and normalizes timeouts, throttling, and provider failures.

Set `MODEL_PROVIDER=bedrock`, `BEDROCK_MODEL_ID`, and `BEDROCK_REGION` to opt in. AWS credentials must come from the standard server-side AWS credential chain. They are never accepted by the frontend or stored in invocation metadata. Deterministic mode remains the CI and offline default.
