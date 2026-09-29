import "server-only";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { getAccessResolution, type AccessTenant } from "../bcos-api";
import { auth } from "./server";

export type TenantRole = AccessTenant["role"];

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
  const selectedTenantId = cookieStore.get("bcos_tenant_id")?.value;
  const selectedTenant = selectedTenantId
    ? access.tenants.find((candidate) => candidate.tenant_id === selectedTenantId)
    : access.tenants.length === 1
      ? access.tenants[0]
      : undefined;

  if (!selectedTenant || !allowedRoles.includes(selectedTenant.role)) redirect("/acesso");
  return selectedTenant;
}
