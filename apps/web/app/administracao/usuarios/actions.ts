"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { assignTenantMembershipAccessRole, inviteTenantMembership, removeTenantMembership, updateTenantMembership, updateTenantMembershipPermissions, updateTenantMembershipStatus, type TenantPermission } from "../../../lib/bcos-api";

function required(formData: FormData, key: string) {
  const value=String(formData.get(key) ?? "").trim();
  if(!value) throw new Error(`${key} é obrigatório.`);
  return value;
}

export async function inviteUserAction(formData: FormData) {
  const role=required(formData,"role");
  if(!["ADMIN","RECEPTION","PROFESSIONAL"].includes(role)) throw new Error("Papel inválido.");
  await inviteTenantMembership({displayName:required(formData,"display_name"),email:required(formData,"email"),role:role as "ADMIN"|"RECEPTION"|"PROFESSIONAL"});
  revalidatePath("/administracao/usuarios");
  redirect("/administracao/usuarios?invited=1");
}

export async function updateUserStatusAction(formData: FormData) {
  const status=required(formData,"status");
  if(status!=="ACTIVE" && status!=="INACTIVE") throw new Error("Situação inválida.");
  await updateTenantMembershipStatus(required(formData,"membership_id"),status);
  revalidatePath("/administracao/usuarios");
}


export async function updateUserAction(formData: FormData) {
  const role=required(formData,"role");
  if(!["ADMIN","RECEPTION","PROFESSIONAL"].includes(role)) throw new Error("Papel inválido.");
  await updateTenantMembership(required(formData,"membership_id"), {
    display_name: required(formData,"display_name"),
    role: role as "ADMIN"|"RECEPTION"|"PROFESSIONAL",
  });
  revalidatePath("/administracao/usuarios");
}

export async function assignUserRoleAction(formData: FormData) {
  await assignTenantMembershipAccessRole(required(formData,"membership_id"),required(formData,"access_role_id"));
  revalidatePath("/administracao/usuarios");
}

export async function removeUserAction(formData: FormData) {
  await removeTenantMembership(required(formData,"membership_id"));
  revalidatePath("/administracao/usuarios");
}

const editablePermissions: TenantPermission[] = [
  "DASHBOARD_VIEW","AGENDA_VIEW","AGENDA_CREATE","AGENDA_EDIT","AGENDA_DELETE","AGENDA_MANAGE","AVAILABILITY_VIEW","CHECKIN_VIEW","CHECKIN_MANAGE",
  "FINANCE_VIEW","FINANCE_CREATE","FINANCE_EDIT","FINANCE_DELETE","FINANCE_MANAGE","ADMIN_VIEW","ADMIN_CONFIG",
  "USER_VIEW","USER_CREATE","USER_EDIT","USER_BLOCK","USER_DELETE","ROLE_MANAGE","USER_ADMIN","PROFESSIONAL_OWN",
];

export async function updateUserPermissionsAction(formData: FormData) {
  const selected = editablePermissions.filter(permission => formData.get(permission) === "on");
  await updateTenantMembershipPermissions(required(formData,"membership_id"), selected);
  revalidatePath("/administracao/usuarios");
}
