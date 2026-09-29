"use server";

import { redirect } from "next/navigation";
import { acceptInvitation, getAccessResolution } from "../../../lib/bcos-api";

export async function acceptPendingInvitation(formData: FormData) {
  const membershipId = String(formData.get("membershipId") ?? "");
  if (!membershipId) throw new Error("Convite inválido.");

  const membership = await acceptInvitation(membershipId);
  const access = await getAccessResolution();
  const tenantIsAvailable = access.tenants.some(
    (tenant) => tenant.tenant_id === membership.tenant_id,
  );

  if (!tenantIsAvailable) {
    redirect("/acesso?invitationAccepted=pendingActivation");
  }

  redirect(`/acesso/tenant/${membership.tenant_id}`);
}
