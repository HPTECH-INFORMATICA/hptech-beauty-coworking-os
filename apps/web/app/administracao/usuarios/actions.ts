"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { assignTenantMembershipAccessRole, inviteTenantMembership, removeTenantMembership, updateTenantMembership, updateTenantMembershipPermissions, updateTenantMembershipStatus, type TenantPermission } from "../../../lib/bcos-api";

function required(formData: FormData, key: string) {
  const value=String(formData.get(key) ?? "").trim();
  if(!value) throw new Error(`${key} é obrigatório.`);
  return value;
}

function actionFailure(error: unknown): string {
  const message = error instanceof Error ? error.message : "";
  if (message.includes("TEAM_INVITATION_EMAIL_FAILED")) return "Não foi possível enviar o convite por e-mail. Tente novamente em alguns instantes.";
  if (message.includes("HTTP 409")) return "Não foi possível concluir porque já existe um vínculo ou cadastro conflitante.";
  if (message.includes("HTTP 403")) return "Seu acesso não permite executar esta alteração.";
  if (message.includes("HTTP 404")) return "O cadastro solicitado não foi encontrado. Atualize a página e tente novamente.";
  if (message.includes("HTTP 422")) return "Revise os dados informados e tente novamente.";
  return "Não foi possível concluir a operação. Nenhuma alteração incompleta foi mantida.";
}

function usersRedirect(params: Record<string,string>) {
  const search = new URLSearchParams(params);
  redirect(`/administracao/usuarios?${search.toString()}`);
}

export async function inviteUserAction(formData: FormData) {
  try {
    await inviteTenantMembership({displayName:required(formData,"display_name"),email:required(formData,"email"),accessRoleId:required(formData,"access_role_id")});
  } catch (error) {
    usersRedirect({error:actionFailure(error)});
  }
  revalidatePath("/administracao/usuarios");
  usersRedirect({invited:"1"});
}

export async function updateUserStatusAction(formData: FormData) {
  try {
    const status=required(formData,"status");
    if(status!=="ACTIVE" && status!=="INACTIVE") throw new Error("Situação inválida.");
    await updateTenantMembershipStatus(required(formData,"membership_id"),status);
  } catch (error) {
    usersRedirect({error:actionFailure(error)});
  }
  revalidatePath("/administracao/usuarios");
  usersRedirect({updated:"1"});
}

export async function updateUserAction(formData: FormData) {
  try {
    await updateTenantMembership(required(formData,"membership_id"), { display_name: required(formData,"display_name") });
  } catch (error) {
    usersRedirect({error:actionFailure(error)});
  }
  revalidatePath("/administracao/usuarios");
  usersRedirect({updated:"1"});
}

export async function assignUserRoleAction(formData: FormData) {
  try {
    await assignTenantMembershipAccessRole(required(formData,"membership_id"),required(formData,"access_role_id"));
  } catch (error) {
    usersRedirect({error:actionFailure(error)});
  }
  revalidatePath("/administracao/usuarios");
  usersRedirect({updated:"1"});
}

export async function removeUserAction(formData: FormData) {
  try {
    await removeTenantMembership(required(formData,"membership_id"));
  } catch (error) {
    usersRedirect({error:actionFailure(error)});
  }
  revalidatePath("/administracao/usuarios");
  usersRedirect({updated:"1"});
}

const editablePermissions: TenantPermission[] = [
  "DASHBOARD_VIEW","AGENDA_VIEW","AGENDA_CREATE","AGENDA_EDIT","AGENDA_DELETE","AGENDA_MANAGE","AVAILABILITY_VIEW","CHECKIN_VIEW","CHECKIN_MANAGE",
  "FINANCE_VIEW","FINANCE_CREATE","FINANCE_EDIT","FINANCE_DELETE","FINANCE_MANAGE","ADMIN_VIEW","ADMIN_CONFIG",
  "USER_VIEW","USER_CREATE","USER_EDIT","USER_BLOCK","USER_DELETE","ROLE_MANAGE","USER_ADMIN","PROFESSIONAL_OWN",
];

export async function updateUserPermissionsAction(formData: FormData) {
  try {
    const selected = editablePermissions.filter(permission => formData.get(permission) === "on");
    await updateTenantMembershipPermissions(required(formData,"membership_id"), selected);
  } catch (error) {
    usersRedirect({error:actionFailure(error)});
  }
  revalidatePath("/administracao/usuarios");
  usersRedirect({updated:"1"});
}
