# BCOS C1 — Neon Auth Production Identity Authority

> "Quem pede um, pede bis."

**Decision:** Neon Auth / Managed Better Auth is the production identity authority for BCOS.

## Boundary

Neon Auth owns credential verification, password lifecycle, sessions, email verification and the stable authenticated user identity. BCOS does not persist passwords, password hashes or MFA secrets.

BCOS owns authorization:
- platform_operators for HPTECH platform authority;
- tenant_memberships for contracting-company authority;
- TenantContext and PlatformContext for access decisions;
- audit evidence for authorization mutations.

The stable Neon Auth user identifier is bound to AuthenticatedIdentity.external_user_id.

## Production verification contract

The FastAPI production verifier accepts only JWT bearer credentials that:
1. have a valid cryptographic signature from the configured Neon Auth JWKS;
2. use an allowed asymmetric signing algorithm;
3. are not expired;
4. match the configured issuer;
5. contain a non-blank subject (sub), used as external_user_id.

Required API configuration:
- BCOS_IDENTITY_PROVIDER=neon
- BCOS_NEON_AUTH_ISSUER=<production Neon Auth issuer>
- BCOS_NEON_AUTH_JWKS_URL=<production branch JWKS URL>

Homologation credentials remain isolated and must not be interpreted as production identity.

## Session boundary

The Next.js application uses Neon Auth for sign-in/sign-out/session lifecycle. It sends a Neon Auth JWT to the FastAPI API when an authenticated API request is required. FastAPI independently verifies that JWT before resolving PlatformContext or TenantContext.

## Environment isolation

Production, preview and development identity endpoints must remain branch/environment scoped. A token from another issuer is rejected even if its signature is otherwise valid.

## No duplicated identity authority

Neon Auth organizations/roles are not the BCOS authorization source. BCOS roles remain in platform_operators and tenant_memberships. This prevents authentication-provider configuration from silently granting tenant or HPTECH permissions.
