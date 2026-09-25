"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import {
  createProfessional,
  createResource,
  createResourceCategory,
  createUnit,
} from "../../lib/bcos-api";

function value(formData: FormData, name: string): string {
  return String(formData.get(name) ?? "").trim();
}

export async function createUnitAction(formData: FormData) {
  await createUnit({ name: value(formData, "name"), timezone: value(formData, "timezone") || "America/Sao_Paulo" });
  revalidatePath("/administracao");
  redirect("/administracao?created=unit");
}

export async function createCategoryAction(formData: FormData) {
  await createResourceCategory({ name: value(formData, "name") });
  revalidatePath("/administracao");
  redirect("/administracao?created=category");
}

export async function createResourceAction(formData: FormData) {
  await createResource({ unitId: value(formData, "unit_id"), categoryId: value(formData, "category_id"), name: value(formData, "name") });
  revalidatePath("/administracao");
  redirect("/administracao?created=resource");
}

export async function createProfessionalAction(formData: FormData) {
  await createProfessional({ name: value(formData, "name"), email: value(formData, "email") || undefined, phone: value(formData, "phone") || undefined });
  revalidatePath("/administracao");
  redirect("/administracao?created=professional");
}
