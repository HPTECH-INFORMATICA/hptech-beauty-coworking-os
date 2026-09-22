"use server";

import { redirect } from "next/navigation";

import { createContractingTenant } from "../../../lib/bcos-api";

function required(formData: FormData, key: string): string {
  const value = String(formData.get(key) ?? "").trim();
  if (!value) throw new Error(`${key} é obrigatório.`);
  return value;
}

export async function createClientAction(formData: FormData) {
  const tenant = await createContractingTenant({
    name: required(formData, "name"),
    slug: required(formData, "slug"),
    legalName: required(formData, "legal_name"),
    tradeName: required(formData, "trade_name"),
    taxId: String(formData.get("tax_id") ?? "").trim() || undefined,
    email: required(formData, "email"),
    phone: String(formData.get("phone") ?? "").trim() || undefined,
    ownerExternalUserId: required(formData, "owner_external_user_id"),
  });
  redirect(`/platform/clientes?created=${encodeURIComponent(tenant.trade_name)}`);
}
