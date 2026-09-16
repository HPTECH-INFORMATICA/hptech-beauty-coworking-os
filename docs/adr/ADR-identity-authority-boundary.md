# ADR — Identity Authority Boundary

> "Quem pede um, pede bis."

## Status

DOCUMENTED CURRENT BOUNDARY / NO NEW AUTHORITY

This ADR records the authentication and authorization boundary already implemented in BCOS. It does not define a production login protocol, token format, session lifecycle or HPTECH Identity integration contract.

## Context

BCOS already enforces authentication, tenant membership and RBAC server-side:

1. FastAPI requires a Bearer credential through `get_authenticated_identity`.
2. `IdentityVerifier` is the trusted adapter boundary. The default `UnconfiguredIdentityVerifier` fails closed.
3. `HomologationIdentityVerifier` exists only as an environment-gated local human-homologation adapter.
4. An authenticated `external_user_id` is resolved against an active tenant membership to create `TenantContext`.
5. `TenantContext` carries tenant, membership, external identity and role.
6. RBAC derives server-side permissions from that role.
7. The current Next.js server adapter uses homologation environment variables to call the API; this is not a user session or production identity mechanism.

## Decision record

The current boundary is preserved as follows:

- BCOS does not mint or cryptographically define production identity credentials.
- BCOS trusts only an explicitly configured `IdentityVerifier` implementation.
- Until a trusted production verifier is configured, authentication remains fail-closed.
- `X-Tenant-Id` selects the requested tenant context but never grants access by itself; active membership for the authenticated external identity remains mandatory.
- Authorization remains server-side through `TenantContext` and RBAC.
- A role-aware frontend shell may only consume identity/role information after an authoritative authenticated-session contract exists. It must not infer role from routes, browser state, query parameters or homologation environment variables.
- `BCOS_HOMOLOGATION_BEARER_TOKEN`, `BCOS_HOMOLOGATION_EXTERNAL_USER_ID` and `BCOS_HUMAN_TENANT_ID` remain homologation/development plumbing. They must not be promoted into a production login/session design.

## Explicitly unresolved

The repository does not currently establish authoritative production semantics for:

- login UX or credential collection;
- token issuer, signing/verification format or key discovery;
- browser session/cookie lifecycle;
- refresh/logout/revocation behavior;
- tenant selection UX for identities with multiple memberships;
- the contract by which HPTECH Identity exposes authenticated identity/session state to the BCOS web application.

These semantics must not be invented from the existing homologation adapter.

## Consequences

- Existing API authorization can continue to evolve independently of the eventual identity provider implementation.
- Production Identity integration can replace/configure the verifier boundary without weakening tenant membership or RBAC.
- The visible role-aware shell remains a controlled gap until the authenticated-session boundary is backed by explicit authority.
- Homologation can continue using the existing environment-gated verifier without representing that mechanism as production readiness.

## Guardrails

- PRD MASTER v1.0 and Architecture Freeze v1.2 remain unchanged.
- Multi-tenant isolation remains mandatory.
- Authorization remains server-side.
- Professional own-scope remains enforced by backend authority.
- No frontend-only role or tenant authorization is accepted.
- No provider-specific production protocol is introduced by this record.

> "Quem pede um, pede bis."
