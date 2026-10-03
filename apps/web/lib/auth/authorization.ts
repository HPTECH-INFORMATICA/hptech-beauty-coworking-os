import "server-only";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { getAccessResolution, type AccessTenant } from "../bcos-api";
import { auth } from "./server";

export type TenantRole = AccessTenant["role"];

const TENANT_COOKIE = "bcos_tenant_id";

export async function requireTenantRole(allowedRoles: readonly TenantRole[]): Promise<AccessTenant> {
  const { data: session } = await auth.getSession();
  if (!session?.user) redirect("/auth/sign-in");

  let access;
  try {
    access = await getAccessResolution();
  } catch (error) {
    console.error(
      "BCOS tenant authorization gate failed:",
      error instanceof Error ? error.message : "unknown error",
    );
    redirect("/acesso");
  }

  const cookieStore = await cookies();
  const selectedTenantId = cookieStore.get(TENANT_COOKIE)?.value;
  if (!selectedTenantId) redirect("/acesso");

  const selectedTenant = access.tenants.find(
    (candidate) => candidate.tenant_id === selectedTenantId,
  );

  if (!selectedTenant || !allowedRoles.includes(selectedTenant.role)) redirect("/acesso");
  return selectedTenant;
}


export type TenantPermission = AccessTenant["permissions"][number];

export async function requireTenantPermission(permission: TenantPermission): Promise<AccessTenant> {
  const tenant = await requireTenantRole(["OWNER","ADMIN","RECEPTION","PROFESSIONAL"]);
  if (!tenant.permissions.includes(permission)) redirect("/acesso");
  return tenant;
}

export async function requireTenantAnyPermission(permissions: readonly TenantPermission[]): Promise<AccessTenant> {
  const tenant = await requireTenantRole(["OWNER","ADMIN","RECEPTION","PROFESSIONAL"]);
  if (!permissions.some(permission => tenant.permissions.includes(permission))) redirect("/acesso");
  return tenant;
}
