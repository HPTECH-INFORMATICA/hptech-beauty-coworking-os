export type PricingRuleDefinitionV1Form = {
  schema_version: 1;
  modality: "HOURLY" | "PERIOD" | "WEEKLY" | "MONTHLY";
  base_price_amount: string;
  overtime: {
    hourly_price_amount: string;
    proportional_until_minutes: number;
    full_hour_from_minutes: number;
    forgiveness_allowed: boolean;
  };
  conflict_penalty?: {
    mode: "FIXED_AMOUNT" | "PERCENTAGE";
    value: string;
  };
};

function value(formData: FormData, name: string): string {
  return String(formData.get(name) ?? "").trim();
}

export function pricingRuleDefinitionFromForm(formData: FormData): PricingRuleDefinitionV1Form {
  const modality = value(formData, "modality");
  if (!["HOURLY", "PERIOD", "WEEKLY", "MONTHLY"].includes(modality)) {
    throw new Error("Modalidade de preço inválida.");
  }

  const definition: PricingRuleDefinitionV1Form = {
    schema_version: 1,
    modality: modality as PricingRuleDefinitionV1Form["modality"],
    base_price_amount: value(formData, "base_price_amount"),
    overtime: {
      hourly_price_amount: value(formData, "overtime_hourly_price_amount"),
      proportional_until_minutes: Number(value(formData, "proportional_until_minutes")),
      full_hour_from_minutes: Number(value(formData, "full_hour_from_minutes")),
      forgiveness_allowed: formData.get("forgiveness_allowed") === "on",
    },
  };

  const penaltyMode = value(formData, "conflict_penalty_mode");
  const penaltyValue = value(formData, "conflict_penalty_value");
  if (penaltyMode && penaltyValue) {
    if (!["FIXED_AMOUNT", "PERCENTAGE"].includes(penaltyMode)) throw new Error("Tipo de penalidade inválido.");
    definition.conflict_penalty = {
      mode: penaltyMode as "FIXED_AMOUNT" | "PERCENTAGE",
      value: penaltyValue,
    };
  }

  return definition;
}
