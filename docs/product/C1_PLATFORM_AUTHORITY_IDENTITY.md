# BCOS C1 — Platform Authority and Production Identity Contract

> "Quem pede um, pede bis."

**Gate:** C1  
**Status:** LOCKED CONTRACT — implementation authority

## 1. Problem being solved

The existing BCOS authorization model starts after a tenant and membership already exist. That is correct for tenant-scoped operations, but it cannot answer the commercial bootstrap questions:

- who at HPTECH creates and administers contracting companies;
- how the first contracting-company OWNER receives access;
- how that OWNER creates/invites tenant users;
- how production login replaces the homologation bearer-token mechanism.

C1 creates that authority boundary without turning HPTECH operators into tenant memberships.

## 2. Separate authorities

### Platform authority

A **PlatformOperator** is an HPTECH-side identity. It is global to the BCOS SaaS control plane and is not stored as an OWNER/ADMIN membership of customer tenants.

Initial platform role:

- `PLATFORM_ADMIN`

Platform permissions:

- `TENANT_CREATE`
- `TENANT_READ`
- `TENANT_LIFECYCLE_MANAGE`
- `TENANT_OWNER_INVITE`
- `PLATFORM_OPERATOR_MANAGE`
- `PLATFORM_AUDIT_READ`

A platform operator must not silently acquire tenant operational permissions.

### Tenant authority

Existing tenant membership roles remain:

- OWNER
- ADMIN
- RECEPTION
- PROFESSIONAL

Existing `TenantContext` remains the authority for tenant-scoped endpoints.

## 3. Production identity boundary

BCOS keeps `AuthenticatedIdentity.external_user_id` as the stable identity binding.

The production verifier must:

1. cryptographically verify the trusted identity token/session;
2. reject missing, expired, invalid or untrusted credentials;
3. return a stable `external_user_id`;
4. fail closed when production identity is not configured.

The current homologation verifier is not a commercial login system and must not become one.

Password credentials, password hashes and MFA secrets must not be stored in BCOS tenant tables. Credential authority belongs to the trusted HPTECH Identity provider/adapter.

## 4. Platform operator persistence

Create a platform-scoped table independent of `tenant_id`:

`platform_operators`

Required fields:

- `id UUID PK`
- `external_user_id VARCHAR(255) UNIQUE NOT NULL`
- `role platform_operator_role NOT NULL`
- `status platform_operator_status NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`
- `disabled_at TIMESTAMPTZ NULL`

Enums:

- `platform_operator_role = PLATFORM_ADMIN`
- `platform_operator_status = ACTIVE | INACTIVE`

No tenant foreign key is allowed.

## 5. Tenant commercial lifecycle

Expand tenant lifecycle from the current operational ACTIVE/INACTIVE concept to an explicit commercial onboarding lifecycle:

- `PENDING_ACTIVATION`
- `ACTIVE`
- `SUSPENDED`
- `INACTIVE`

Rules:

- platform authority creates the tenant in `PENDING_ACTIVATION`;
- tenant operations require `ACTIVE`;
- suspension blocks tenant operational access without deleting business data;
- lifecycle changes are audited.

Migration implementation must preserve existing ACTIVE/INACTIVE production rows.

## 6. Contracting-company profile

The tenant record remains the tenant identity. Commercial/legal profile data belongs in a tenant-scoped one-to-one profile rather than overloading operational units.

`tenant_profiles` minimum contract:

- `tenant_id UUID PK/FK`
- `legal_name VARCHAR(200) NOT NULL`
- `trade_name VARCHAR(200) NOT NULL`
- `tax_id VARCHAR(32) NULL`
- `email VARCHAR(255) NOT NULL`
- `phone VARCHAR(40) NULL`
- `created_at`
- `updated_at`

Address and subscription/plan details are subsequent C1/C2 contract slices; do not invent them in this slice.

## 7. First OWNER invitation

Platform onboarding is atomic at the application-service boundary:

1. PLATFORM_ADMIN creates tenant + tenant profile;
2. creates an OWNER membership with status `INVITED`;
3. the membership binds to the trusted identity `external_user_id`;
4. trusted Identity owns delivery/acceptance of first-access credentials;
5. after verified first access/acceptance, membership becomes `ACTIVE`;
6. tenant becomes `ACTIVE` only when onboarding activation requirements are satisfied.

No default password is generated or persisted by BCOS.

## 8. Tenant user administration

After activation:

- OWNER may invite ADMIN, RECEPTION and PROFESSIONAL;
- ADMIN may invite roles allowed by tenant RBAC policy but cannot create another OWNER unless a later ownership-transfer contract explicitly permits it;
- RECEPTION cannot administer identities;
- PROFESSIONAL cannot administer identities;
- invitation does not authorize access until membership is ACTIVE.

Every mutation is tenant-scoped and audited.

## 9. API boundaries

### Platform API

Prefix: `/api/v1/platform`

Required C1 endpoints:

- `GET /platform/tenants`
- `POST /platform/tenants`
- `GET /platform/tenants/{tenant_id}`
- `PATCH /platform/tenants/{tenant_id}/status`
- `POST /platform/tenants/{tenant_id}/owner-invitations`

These endpoints use `PlatformContext`, never `X-Tenant-Id` as authorization authority.

### Tenant administration API

Prefix remains tenant-authorized under `X-Tenant-Id`:

- `GET /api/v1/admin/memberships`
- `POST /api/v1/admin/memberships/invitations`
- `PATCH /api/v1/admin/memberships/{membership_id}/status`

These endpoints use `TenantContext` and TENANT_ADMIN permission.

## 10. Frontend surfaces

C1 requires two distinct shells:

### HPTECH Console

Route boundary: `/platform`

Initial pages:

- `/platform/clientes`
- `/platform/clientes/novo`
- `/platform/clientes/[tenantId]`

Purpose: HPTECH customer onboarding and lifecycle administration.

### Tenant administration

Route boundary: `/administracao`

Initial pages:

- `/administracao/empresa`
- `/administracao/usuarios`

C2 expands this shell with units, resources, professionals and pricing.

## 11. Audit requirements

Audit at minimum:

- platform operator created/disabled;
- tenant created;
- tenant status changed;
- first OWNER invited;
- tenant membership invited/activated/deactivated.

Actor identity, target, timestamp and tenant id (when applicable) must be recoverable.

## 12. Acceptance tests

C1 is not complete until tests prove:

1. tenant OWNER cannot call platform endpoints;
2. PLATFORM_ADMIN cannot gain tenant operation rights merely by platform role;
3. inactive platform operator is rejected;
4. inactive/suspended tenant is rejected for tenant operations;
5. PLATFORM_ADMIN can create tenant and first OWNER invitation;
6. OWNER can invite allowed tenant users;
7. RECEPTION/PROFESSIONAL cannot administer users;
8. invitation alone does not grant active access;
9. cross-tenant membership access remains denied;
10. production identity configuration fails closed.

## 13. Explicit non-goals for this contract

C1 does not implement:

- resource administration (C2);
- commercial calendar/pricing UX (C3);
- administrative finance (C4/C5);
- ownership transfer;
- silent support impersonation;
- password storage inside BCOS.

Those remain governed by the commercial baseline.

> "Quem pede um, pede bis."
