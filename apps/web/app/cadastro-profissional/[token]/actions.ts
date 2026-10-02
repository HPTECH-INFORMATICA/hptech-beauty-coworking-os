"use server";
import { redirect } from "next/navigation";
import { submitPublicProfessionalOnboarding } from "../../lib/bcos-api";

export async function submitProfessionalRegistration(token: string, formData: FormData) {
  const acceptedDocumentIds = formData.getAll("accepted_document_ids").map(String);
  await submitPublicProfessionalOnboarding(token, {
    name: String(formData.get("name") ?? "").trim(),
    email: String(formData.get("email") ?? "").trim(),
    phone: String(formData.get("phone") ?? "").trim() || null,
    profession: String(formData.get("profession") ?? "").trim() || null,
    council_type: String(formData.get("council_type") ?? "").trim() || null,
    council_number: String(formData.get("council_number") ?? "").trim() || null,
    accepted_document_ids: acceptedDocumentIds,
  });
  redirect(`/cadastro-profissional/${encodeURIComponent(token)}?enviado=1`);
}
