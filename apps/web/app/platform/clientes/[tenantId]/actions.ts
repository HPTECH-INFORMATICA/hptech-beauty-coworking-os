"use server";

import { revalidatePath } from "next/cache";

import { inviteContractingTenantOwner, updateContractingTenantStatus, type ContractingTenant } from "../../../../lib/bcos-api";

export async function updateClientStatusAction(formData: FormData) {
  const tenantId = String(formData.get("tenant_id") ?? "");
  const status = String(formData.get("status") ?? "") as ContractingTenant["status"];
  await updateContractingTenantStatus(tenantId, status);
  revalidatePath("/platform/clientes");
  revalidatePath(`/platform/clientes/${tenantId}`);
}

export async function inviteOwnerAction(formData: FormData) {
  "use server";
  const tenantId = String(formData.get("tenant_id") ?? "").trim();
  const email = String(formData.get("owner_email") ?? "").trim();
  if (!tenantId || !email) return;
  await inviteContractingTenantOwner(tenantId, email);
  revalidatePath(`/platform/clientes/${tenantId}`);
}
