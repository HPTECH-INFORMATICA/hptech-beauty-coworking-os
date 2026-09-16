# BCOS — Production Delivery Audit

> "Quem pede um, pede bis."

## Status

AUDITED / DELIVERY NOT YET HOMOLOGATED

This record captures deployment-relevant facts already present in the repository. It does not declare any environment deployed or production-ready, and it does not introduce provider credentials or production Identity semantics.

## Canonical deploy topology

The project baseline identifies three independently runnable surfaces:

- Web: Next.js application in `apps/web`, intended for Vercel.
- API: FastAPI application in `services/api`, intended for Render.
- Worker: Python background process in `services/worker`, intended for Render.

The repository currently has no materialized provider configuration in `infra/`; that directory contains only `.gitkeep` before this audit.

## Web execution boundary

`apps/web/package.json` exposes `next build` and `next dev`. The workspace requires Node >=22.21.0 and pnpm >=11.17.0.

The server-side BCOS API adapter currently requires:

- `BCOS_API_BASE_URL` — API origin; local fallback is `http://127.0.0.1:8010`.
- `BCOS_HOMOLOGATION_BEARER_TOKEN` — required by the current homologation adapter.
- `BCOS_HUMAN_TENANT_ID` — required by the current homologation adapter.

The last two variables are explicitly homologation plumbing. Their existence does not authorize using them as a production login/session design. Therefore a public production Web delivery cannot be called complete while the trusted production Identity/session contract remains unresolved.

## API execution boundary

The API package requires Python >=3.12,<3.13 and includes Uvicorn. The ASGI application is `bcos_api.main:app`.

The repository-local executable `python -m bcos_api` is development-oriented: its current `__main__` binds Uvicorn to `127.0.0.1:8010`. A production platform must instead launch the ASGI application with a provider-supplied external bind/port, without changing application authority.

Known runtime environment requirements include:

- `DATABASE_URL` — mandatory PostgreSQL URL.
- `BCOS_HOMOLOGATION_BEARER_TOKEN` + `BCOS_HOMOLOGATION_EXTERNAL_USER_ID` only when intentionally running the existing homologation verifier.

If the homologation verifier pair is absent, authentication intentionally fails closed until a trusted IdentityVerifier is configured.

The API exposes `/health`, returning the BCOS API service health payload. This is a process health endpoint; this audit does not promote it to database-readiness evidence.

## Worker execution boundary

The worker package requires Python >=3.12,<3.13 and defines the executable script:

`bcos-worker = bcos_worker.main:main`

It requires `DATABASE_URL` and starts the already-implemented sequential Outbox runtime. API and Worker must use the same BCOS database authority for Outbox/Billing continuity; no other HPTECH product database may be substituted.

## Database migration boundary

Alembic remains the schema migration authority and the Quality Gate enforces a single migration head. This audit does not choose an automatic migration-on-deploy policy because ownership/timing of production migrations is not yet established by a locked deployment contract.

Production deployment must not silently run migrations concurrently from API and Worker startup.

## Current blockers to production homologation

1. Trusted production Identity/session integration is unresolved; homologation bearer credentials must not be presented as the production authentication model.
2. Provider-specific deployment manifests/settings have not yet been materialized and validated against actual Vercel/Render services.
3. Production environment values and service URLs have not been verified by this repository audit.
4. Database migration execution ownership for production delivery has not yet been locked.
5. No deployed smoke test evidence exists in this record for Web → API → PostgreSQL → Worker → Billing.

## Safe next delivery slice

Provider-neutral deployment documentation and startup contracts may be materialized from the facts above. Actual Vercel/Render creation or configuration must be verified against the target services and environment before production can be homologated.

No T27 threshold, Pricing administration, Owner Dashboard or production Identity semantics are authorized by this audit.

> "Quem pede um, pede bis."
