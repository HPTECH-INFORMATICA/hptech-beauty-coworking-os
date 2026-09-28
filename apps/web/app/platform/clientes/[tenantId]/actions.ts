"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

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
  try {
    await inviteContractingTenantOwner(tenantId, email);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (message.includes("HTTP 422")) {
      redirect(`/platform/clientes/${tenantId}?ownerInvite=account-required`);
    }
    if (message.includes("HTTP 409")) {
      redirect(`/platform/clientes/${tenantId}?ownerInvite=already-linked`);
    }
    throw error;
  }
  revalidatePath(`/platform/clientes/${tenantId}`);
  redirect(`/platform/clientes/${tenantId}?ownerInvite=sent`);
}
