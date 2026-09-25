"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import {
  createProfessional,
  createResource,
  createResourceCategory,
  createUnit,
  updateReceptionHours,
  updateTenantProfile,
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


export async function updateTenantProfileAction(formData: FormData) {
  await updateTenantProfile({
    legal_name: value(formData, "legal_name"),
    trade_name: value(formData, "trade_name"),
    tax_id: value(formData, "tax_id") || null,
    email: value(formData, "email"),
    phone: value(formData, "phone") || null,
  });
  revalidatePath("/administracao");
  redirect("/administracao?updated=profile");
}

export async function updateReceptionHoursAction(formData: FormData) {
  const unitId = value(formData, "unit_id");
  const hours = Array.from({ length: 7 }, (_, day) => {
    const isClosed = formData.get(`closed_${day}`) === "on";
    return {
      day_of_week: day,
      opens_at: isClosed ? null : value(formData, `opens_${day}`),
      closes_at: isClosed ? null : value(formData, `closes_${day}`),
      is_closed: isClosed,
    };
  });
  await updateReceptionHours(unitId, hours);
  revalidatePath("/administracao");
  redirect("/administracao?updated=reception-hours");
}
