import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { createPricingRuleAction } from "../app/administracao/actions";

import TenantAdministrationPage from "../app/administracao/page";
import UsersAdminPage from "../app/administracao/usuarios/page";
import {
  getPricingRules,
  getProfessionals,
  getReceptionHours,
  getResourceCategories,
  getResources,
  getTenantMemberships,
  getTenantProfile,
  getUnits,
  createPricingRule,
} from "../lib/bcos-api";

vi.mock("../lib/bcos-api", () => ({
  getPricingRules: vi.fn(),
  getProfessionals: vi.fn(),
  getReceptionHours: vi.fn(),
  getResourceCategories: vi.fn(),
  getResources: vi.fn(),
  getTenantMemberships: vi.fn(),
  getTenantProfile: vi.fn(),
  getUnits: vi.fn(),
  createPricingRule: vi.fn(),
}));

const mockedGetUnits = vi.mocked(getUnits);
const mockedGetReceptionHours = vi.mocked(getReceptionHours);

describe("tenant administration", () => {
  beforeEach(() => {
    vi.mocked(getTenantProfile).mockResolvedValue({ legal_name: "La Beauté Ltda", trade_name: "La Beauté", tax_id: null, email: "contato@example.com", phone: null });
    mockedGetUnits.mockResolvedValue([
      { id: "unit-1", name: "Batel", timezone: "America/Sao_Paulo", active: true, created_at: "", updated_at: "" },
      { id: "unit-2", name: "Centro", timezone: "America/Sao_Paulo", active: true, created_at: "", updated_at: "" },
    ]);
    vi.mocked(getResourceCategories).mockResolvedValue([]);
    vi.mocked(getResources).mockResolvedValue([]);
    vi.mocked(getProfessionals).mockResolvedValue([]);
    vi.mocked(getPricingRules).mockResolvedValue([]);
    mockedGetReceptionHours.mockImplementation(async (unitId) => unitId === "unit-1"
      ? [{ day_of_week: 0, opens_at: "08:00:00", closes_at: "18:00:00", is_closed: false }]
      : [{ day_of_week: 0, opens_at: "09:00:00", closes_at: "17:00:00", is_closed: false }]);
    vi.mocked(getTenantMemberships).mockResolvedValue([]);
  });

  it("loads and renders reception hours for every unit", async () => {
    render(await TenantAdministrationPage());
    expect(mockedGetReceptionHours).toHaveBeenCalledWith("unit-1");
    expect(mockedGetReceptionHours).toHaveBeenCalledWith("unit-2");
    expect(screen.getByRole("button", { name: "Salvar horários de Batel" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salvar horários de Centro" })).toBeInTheDocument();
  });

  it("renders users as administration content without a legacy product shell", async () => {
    render(await UsersAdminPage({ searchParams: Promise.resolve({}) }));
    expect(screen.getByRole("heading", { level: 1, name: "Usuários e acessos" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Configurações" })).toHaveAttribute("href", "/administracao");
    expect(document.querySelector(".tenant-admin-shell")).not.toBeInTheDocument();
  });
  it("maps the commercial pricing form to the frozen V1 definition", async () => {
    const form = new FormData();
    form.set("name", "Sala por hora");
    form.set("modality", "HOURLY");
    form.set("base_price_amount", "120.00");
    form.set("overtime_hourly_price_amount", "150.00");
    form.set("proportional_until_minutes", "29");
    form.set("full_hour_from_minutes", "30");
    form.set("forgiveness_allowed", "on");
    form.set("priority", "100");

    await expect(createPricingRuleAction(form)).rejects.toBeDefined();

    expect(vi.mocked(createPricingRule)).toHaveBeenCalledWith(expect.objectContaining({
      name: "Sala por hora",
      priority: 100,
      ruleDefinition: {
        schema_version: 1,
        modality: "HOURLY",
        base_price_amount: "120.00",
        overtime: {
          hourly_price_amount: "150.00",
          proportional_until_minutes: 29,
          full_hour_from_minutes: 30,
          forgiveness_allowed: true,
        },
      },
    }));
  });
});
