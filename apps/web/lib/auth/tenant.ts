import "server-only";

import { cookies } from "next/headers";

import { getAccessResolution, type AccessTenant } from "../bcos-api";

const TENANT_COOKIE = "bcos_tenant_id";

export async function resolveSelectedTenant(): Promise<AccessTenant> {
  const access = await getAccessResolution();
  const cookieStore = await cookies();
  const selectedId = cookieStore.get(TENANT_COOKIE)?.value;
  const selected = selectedId
    ? access.tenants.find((tenant) => tenant.tenant_id === selectedId)
    : undefined;

  if (selected) return selected;
  if (access.tenants.length === 1) return access.tenants[0];

  throw new Error("Selecione um coworking autorizado antes de acessar dados do tenant.");
}

export async function persistSelectedTenant(tenantId: string): Promise<AccessTenant> {
  const access = await getAccessResolution();
  const selected = access.tenants.find((tenant) => tenant.tenant_id === tenantId);
  if (!selected) throw new Error("Tenant selecionado não está autorizado para esta identidade.");

  const cookieStore = await cookies();
  cookieStore.set(TENANT_COOKIE, selected.tenant_id, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
  });
  return selected;
}
