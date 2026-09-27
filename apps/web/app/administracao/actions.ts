"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import {
  createPricingRule,
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

export async function createPricingRuleAction(formData: FormData) {
  const definitionText = value(formData, "rule_definition");
  let ruleDefinition: Record<string, unknown>;
  try {
    const parsed: unknown = JSON.parse(definitionText);
    if (parsed === null || Array.isArray(parsed) || typeof parsed !== "object") throw new Error("Pricing rule definition must be an object.");
    ruleDefinition = parsed as Record<string, unknown>;
  } catch {
    throw new Error("A definição da regra deve ser um objeto JSON válido.");
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
