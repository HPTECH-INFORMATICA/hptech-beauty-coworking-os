"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import {
  createPricingRule,
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

export async function createPricingRuleAction(formData: FormData) {
  const modality = value(formData, "modality");
  if (!["HOURLY", "PERIOD", "WEEKLY", "MONTHLY"].includes(modality)) throw new Error("Modalidade de preço inválida.");

  const basePriceAmount = value(formData, "base_price_amount");
  const overtimeHourlyPriceAmount = value(formData, "overtime_hourly_price_amount");
  const proportionalUntilMinutes = Number(value(formData, "proportional_until_minutes"));
  const fullHourFromMinutes = Number(value(formData, "full_hour_from_minutes"));

  const ruleDefinition: Record<string, unknown> = {
    schema_version: 1,
    modality,
    base_price_amount: basePriceAmount,
    overtime: {
      hourly_price_amount: overtimeHourlyPriceAmount,
      proportional_until_minutes: proportionalUntilMinutes,
      full_hour_from_minutes: fullHourFromMinutes,
      forgiveness_allowed: formData.get("forgiveness_allowed") === "on",
    },
  };

  const penaltyMode = value(formData, "conflict_penalty_mode");
  const penaltyValue = value(formData, "conflict_penalty_value");
  if (penaltyMode && penaltyValue) {
    if (!["FIXED_AMOUNT", "PERCENTAGE"].includes(penaltyMode)) throw new Error("Tipo de penalidade inválido.");
    ruleDefinition.conflict_penalty = { mode: penaltyMode, value: penaltyValue };
  }

  await createPricingRule({
    name: value(formData, "name"),
    unitId: value(formData, "unit_id") || undefined,
    categoryId: value(formData, "category_id") || undefined,
    priority: Number(value(formData, "priority") || "100"),
    ruleDefinition,
    validFrom: value(formData, "valid_from") ? new Date(value(formData, "valid_from")).toISOString() : undefined,
    validUntil: value(formData, "valid_until") ? new Date(value(formData, "valid_until")).toISOString() : undefined,
  });
  revalidatePath("/administracao");
  redirect("/administracao?created=pricing-rule");
}
