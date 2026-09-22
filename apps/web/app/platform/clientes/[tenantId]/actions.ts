"use server";

import { revalidatePath } from "next/cache";

import { updateContractingTenantStatus, type ContractingTenant } from "../../../../lib/bcos-api";

export async function updateClientStatusAction(formData: FormData) {
  const tenantId = String(formData.get("tenant_id") ?? "");
  const status = String(formData.get("status") ?? "") as ContractingTenant["status"];
  await updateContractingTenantStatus(tenantId, status);
  revalidatePath("/platform/clientes");
  revalidatePath(`/platform/clientes/${tenantId}`);
}
