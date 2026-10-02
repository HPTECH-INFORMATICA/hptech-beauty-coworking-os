"use server";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { publishPlatformOnboardingTerms } from "../../../lib/bcos-api";

export async function publishPlatformTermsAction(formData: FormData) {
  await publishPlatformOnboardingTerms({
    version: String(formData.get("version") ?? "").trim(),
    title: String(formData.get("title") ?? "").trim(),
    content: String(formData.get("content") ?? "").trim(),
  });
  revalidatePath("/platform/termos");
  redirect("/platform/termos?published=1");
}
