"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import {
  createPricingRule,
  createProfessional,
  createResource,
  createResourceCategory,
  deleteResourceCategory,
  createUnit,
  deleteResource,
  deleteUnit,
  updateReceptionHours,
  updateResourceCategory,
  updateResource,
  updateProfessional,
  updateTenantProfile,
  updateUnit,
} from "../../lib/bcos-api";
import { pricingRuleDefinitionFromForm } from "./pricing-form";

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
  await createProfessional({ name: value(formData, "name"), email: value(formData, "email") || undefined, phone: value(formData, "phone") || undefined, profession: value(formData, "profession") || undefined, councilType: value(formData, "council_type") || undefined, councilNumber: value(formData, "council_number") || undefined });
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

export async function createPricingRuleAction(formData: FormData) {
  await createPricingRule({
    name: value(formData, "name"),
    unitId: value(formData, "unit_id") || undefined,
    categoryId: value(formData, "category_id") || undefined,
    priority: Number(value(formData, "priority") || "100"),
    ruleDefinition: pricingRuleDefinitionFromForm(formData),
    validFrom: value(formData, "valid_from") ? new Date(value(formData, "valid_from")).toISOString() : undefined,
    validUntil: value(formData, "valid_until") ? new Date(value(formData, "valid_until")).toISOString() : undefined,
  });
  revalidatePath("/administracao");
  redirect("/administracao?created=pricing-rule");
}

export async function updateUnitAction(formData: FormData) {
  await updateUnit(value(formData, "unit_id"), {
    name: value(formData, "name"),
    timezone: value(formData, "timezone"),
    active: formData.get("active") === "on",
  });
  revalidatePath("/administracao");
  redirect("/administracao?updated=unit#unidades");
}

export async function updateResourceAction(formData: FormData) {
  await updateResource(value(formData, "resource_id"), {
    name: value(formData, "name"),
    operational_status: value(formData, "operational_status"),
    buffer_before_minutes: Number(value(formData, "buffer_before_minutes") || "0"),
    buffer_after_minutes: Number(value(formData, "buffer_after_minutes") || "0"),
    active: formData.get("active") === "on",
  });
  revalidatePath("/administracao");
  redirect("/administracao?updated=resource#espacos");
}

export async function updateProfessionalAction(formData: FormData) {
  await updateProfessional(value(formData, "professional_id"), {
    name: value(formData, "name"),
    email: value(formData, "email") || null,
    phone: value(formData, "phone") || null,
    profession: value(formData, "profession") || null,
    council_type: value(formData, "council_type") || null,
    council_number: value(formData, "council_number") || null,
    status: value(formData, "status"),
  });
  revalidatePath("/administracao");
  redirect("/administracao?updated=professional#profissionais");
}

export async function deleteUnitAction(formData: FormData) {
  await deleteUnit(value(formData, "unit_id"));
  revalidatePath("/administracao");
  redirect("/administracao?deleted=unit#unidades");
}

export async function deleteResourceAction(formData: FormData) {
  await deleteResource(value(formData, "resource_id"));
  revalidatePath("/administracao");
  redirect("/administracao?deleted=resource#espacos");
}


export async function updateCategoryAction(formData: FormData) {
  await updateResourceCategory(value(formData, "category_id"), {
    name: value(formData, "name"),
    active: formData.get("active") === "on",
  });
  revalidatePath("/administracao");
  redirect("/administracao?updated=category#espacos");
}

export async function deleteCategoryAction(formData: FormData) {
  await deleteResourceCategory(value(formData, "category_id"));
  revalidatePath("/administracao");
  redirect("/administracao?deleted=category#espacos");
}
