"use server";

import { redirect } from "next/navigation";
import { acceptInvitation } from "../../../lib/bcos-api";

export async function acceptPendingInvitation(formData: FormData) {
  const membershipId = String(formData.get("membershipId") ?? "");
  if (!membershipId) throw new Error("Convite inválido.");
  const membership = await acceptInvitation(membershipId);
  redirect(`/acesso/tenant/${membership.tenant_id}`);
}
