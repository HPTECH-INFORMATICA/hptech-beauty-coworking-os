"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { inviteTenantMembership, updateTenantMembershipStatus } from "../../../lib/bcos-api";

function required(formData: FormData, key: string) {
  const value=String(formData.get(key) ?? "").trim();
  if(!value) throw new Error(`${key} é obrigatório.`);
  return value;
}

export async function inviteUserAction(formData: FormData) {
  const role=required(formData,"role");
  if(!["ADMIN","RECEPTION","PROFESSIONAL"].includes(role)) throw new Error("Papel inválido.");
  await inviteTenantMembership({externalUserId:required(formData,"external_user_id"),role:role as "ADMIN"|"RECEPTION"|"PROFESSIONAL"});
  revalidatePath("/administracao/usuarios");
  redirect("/administracao/usuarios?invited=1");
}

export async function updateUserStatusAction(formData: FormData) {
  const status=required(formData,"status");
  if(status!=="ACTIVE" && status!=="INACTIVE") throw new Error("Situação inválida.");
  await updateTenantMembershipStatus(required(formData,"membership_id"),status);
  revalidatePath("/administracao/usuarios");
}
