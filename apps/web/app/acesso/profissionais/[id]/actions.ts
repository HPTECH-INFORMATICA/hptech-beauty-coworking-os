"use server";
import { redirect } from "next/navigation";
import { acceptProfessionalInvitation } from "../../../../lib/bcos-api";

export async function acceptProfessionalAccess(formData: FormData) {
  const invitationId = String(formData.get("invitationId") ?? "").trim();
  if (!invitationId) throw new Error("Convite profissional inválido.");
  const invitation = await acceptProfessionalInvitation(invitationId);
  redirect(`/acesso/tenant/${invitation.tenant_id}`);
}
