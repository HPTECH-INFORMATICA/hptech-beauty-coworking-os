# BCOS — Production Startup Contracts

> "Quem pede um, pede bis."

## Status

MATERIALIZED PROVIDER-NEUTRAL CONTRACT / NOT DEPLOYED

This document converts the audited runtime facts into provider-neutral startup contracts. It does not create Vercel or Render services, does not supply secrets, and does not declare production homologated.

## Web

Runtime: Next.js 16 / Node >=22.21.0 / pnpm >=11.17.0.

Repository location: `apps/web`.

Build contract from repository root:

```text
pnpm install --frozen-lockfile
pnpm --filter @hptech/bcos-web build
```

Runtime contract:

```text
pnpm --filter @hptech/bcos-web exec next start
```

Required server environment for the current adapter:

```text
BCOS_API_BASE_URL=<deployed BCOS API origin>
BCOS_HOMOLOGATION_BEARER_TOKEN=<homologation only>
BCOS_HUMAN_TENANT_ID=<homologation only>
```

The homologation variables above are not a production authentication design. Until the trusted production Identity/session contract exists, this startup contract can support controlled homologation but cannot close the public production Identity gap.

## API

Runtime: Python >=3.12,<3.13.

Repository location: `services/api`.

Install contract:

```text
python -m pip install ./services/api
```

Production ASGI start contract:

```text
uvicorn bcos_api.main:app --host 0.0.0.0 --port ${PORT}
```

The repository-local `python -m bcos_api` remains a local-development entry point because it binds `127.0.0.1:8010`.

Required runtime environment:

```text
DATABASE_URL=<BCOS PostgreSQL URL>
```

Homologation-only verifier pair, when intentionally used:

```text
BCOS_HOMOLOGATION_BEARER_TOKEN=<secret>
BCOS_HOMOLOGATION_EXTERNAL_USER_ID=<external user id>
```

Absent an explicitly configured trusted verifier, authentication remains fail-closed by design.

Health contract:

```text
GET /health
```

A successful `/health` proves the API process can serve the application endpoint. It is not, by itself, proof that PostgreSQL, Worker or Billing are ready.

## Worker

Runtime: Python >=3.12,<3.13.

Repository location: `services/worker`.

Install contract:

```text
python -m pip install ./services/worker
```

Start contract:

```text
bcos-worker
```

Required runtime environment:

```text
DATABASE_URL=<same BCOS PostgreSQL authority used by API>
```

The Worker is a separate long-running process and must not be folded into the Web or API process. Its Outbox/Billing transaction boundaries remain unchanged.

## Schema migration

Alembic is the schema migration authority. The repository Quality Gate proves a single migration head, but production migration execution ownership is not yet locked.

Until that deployment decision exists:

- do not attach Alembic migration execution independently to both API and Worker startup;
- do not make application process boot responsible for an implicit schema mutation;
- treat production migration execution as an explicit release operation requiring one owner.

This guardrail avoids concurrent migration races without inventing the eventual release mechanism.

## Provider mapping

The locked project stack maps Web to Vercel and API/Worker to Render. These startup contracts are intentionally provider-neutral commands that can be entered into those services after the actual target services and environment are verified.

No `vercel.json`, Render Blueprint, Dockerfile or other provider manifest is introduced here because repository evidence alone does not establish the target service IDs, domains, region, plan, secret values, database connection or migration release owner.

## Production evidence gate

Production Delivery can only be homologated after evidence exists for all of the following:

1. Web build and runtime on the target deployment service.
2. API external startup using the provider port and successful `/health`.
3. API connection to the independent BCOS PostgreSQL database.
4. Worker long-running startup against that same BCOS database.
5. Explicit, single-owner Alembic migration execution.
6. Trusted production Identity/session integration, or an explicitly scoped homologation environment that is not represented as public production authentication.
7. End-to-end smoke evidence: Web → API → PostgreSQL → Worker/Outbox → Billing → Finance.

No T27 threshold, Pricing administration, Owner Dashboard or new Identity semantics are authorized by this contract.

> "Quem pede um, pede bis."
