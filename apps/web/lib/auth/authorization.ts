import "server-only";

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

  const selectedTenant = access.tenants.find(
    (candidate) => candidate.destination === "/" && allowedRoles.includes(candidate.role),
  );

  if (!selectedTenant) redirect("/acesso");
  return selectedTenant;
}
